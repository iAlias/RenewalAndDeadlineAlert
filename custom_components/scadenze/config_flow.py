"""Flussi di configurazione: voce, opzioni della voce e scadenze (spec §7)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_USER,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryData,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DATA_NASCITA,
    CONF_IMMATRICOLAZIONE,
    CONF_NOME,
    CONF_NOTIFICHE_ATTIVE,
    CONF_ORARIO_NOTIFICA,
    CONF_PREAVVISI,
    CONF_SENSORE_KM,
    CONF_SERVIZIO_NOTIFICA,
    CONF_TIPO,
    CONF_TIPO_VEICOLO,
    DOMAIN,
    PREDEFINITO_ORARIO_NOTIFICA,
    PREDEFINITO_PREAVVISI,
    PREDEFINITO_SERVIZIO_NOTIFICA,
    SUBENTRY_SCADENZA,
    TIPI_VOCE,
    TIPO_CASA,
    TIPO_GENERICA,
    TIPO_PERSONA,
    TIPO_VEICOLO,
    VEICOLO_AUTO,
    VEICOLO_MOTO,
)
from .modelli import (
    CAMPO_INTERVALLO_KM,
    CAMPO_INTERVALLO_MESI,
    CAMPO_KM_ULTIMO_RINNOVO,
    CAMPO_MESE_SCADENZA_BOLLO,
    CAMPO_MODELLI,
    CAMPO_MODELLO,
    CAMPO_NOME,
    CAMPO_RICORRENZA,
    CAMPO_SCADENZA,
    CAMPO_ULTIMO_RINNOVO,
    MODELLI,
    RICORRENZE,
    ErroreForm,
    costruisci_scadenza,
    modelli_per_tipo,
    modelli_raccomandati,
    valori_da_scadenza,
    valori_suggeriti,
)
from .modello_dati import Scadenza, Voce
from .promemoria import PreavvisiNonValidi, analizza_preavvisi, formatta_preavvisi

_SCHEMA_SOLO_NOME = vol.Schema({vol.Required(CONF_NOME): selector.TextSelector()})


def _numero(minimo: int, massimo: int, unita: str) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=minimo,
            max=massimo,
            step=1,
            mode=selector.NumberSelectorMode.BOX,
            unit_of_measurement=unita,
        )
    )


_SELETTORI_CAMPI: dict[str, Any] = {
    CAMPO_SCADENZA: selector.DateSelector(),
    CAMPO_MESE_SCADENZA_BOLLO: selector.DateSelector(),
    CAMPO_ULTIMO_RINNOVO: selector.DateSelector(),
    CAMPO_INTERVALLO_MESI: _numero(1, 240, "mesi"),
    CAMPO_KM_ULTIMO_RINNOVO: _numero(0, 2_000_000, "km"),
    CAMPO_INTERVALLO_KM: _numero(0, 100_000, "km"),
    CAMPO_RICORRENZA: selector.SelectSelector(
        selector.SelectSelectorConfig(options=list(RICORRENZE), translation_key=CAMPO_RICORRENZA)
    ),
}


def _schema_dettagli(chiave: str) -> vol.Schema:
    campi: dict[Any, Any] = {vol.Required(CAMPO_NOME): selector.TextSelector()}
    for campo in MODELLI[chiave].campi:
        campi[vol.Required(campo)] = _SELETTORI_CAMPI[campo]
    return vol.Schema(campi)


def _schema_opzioni(veicolo: bool) -> vol.Schema:
    campi: dict[Any, Any] = {}
    if veicolo:
        campi[vol.Optional(CONF_SENSORE_KM)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
    campi[vol.Required(CONF_NOTIFICHE_ATTIVE)] = selector.BooleanSelector()
    campi[vol.Required(CONF_SERVIZIO_NOTIFICA)] = selector.TextSelector()
    campi[vol.Optional(CONF_PREAVVISI, default="")] = selector.TextSelector()
    campi[vol.Required(CONF_ORARIO_NOTIFICA)] = selector.TimeSelector()
    return vol.Schema(campi)


class ScadenzeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Crea una voce: veicolo, casa, persona o generica; poi le sue prime scadenze."""

    VERSION = 1

    def __init__(self) -> None:
        self._dati_voce: dict[str, Any] = {}
        self._coda_modelli: list[str] = []
        self._scadenze_raccolte: list[Scadenza] = []

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return ScadenzeOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_SCADENZA: ScadenzaSubentryFlow}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="user", menu_options=list(TIPI_VOCE))

    async def async_step_veicolo(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        schema = vol.Schema(
            {
                vol.Required(CONF_NOME): selector.TextSelector(),
                vol.Required(CONF_TIPO_VEICOLO, default=VEICOLO_AUTO): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[VEICOLO_AUTO, VEICOLO_MOTO], translation_key=CONF_TIPO_VEICOLO
                    )
                ),
                vol.Required(CONF_IMMATRICOLAZIONE): selector.DateSelector(),
            }
        )
        return await self._passo_voce(TIPO_VEICOLO, schema, user_input, CONF_IMMATRICOLAZIONE)

    async def async_step_casa(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._passo_voce(TIPO_CASA, _SCHEMA_SOLO_NOME, user_input)

    async def async_step_persona(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        schema = vol.Schema(
            {
                vol.Required(CONF_NOME): selector.TextSelector(),
                vol.Required(CONF_DATA_NASCITA): selector.DateSelector(),
            }
        )
        return await self._passo_voce(TIPO_PERSONA, schema, user_input, CONF_DATA_NASCITA)

    async def async_step_generica(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._passo_voce(TIPO_GENERICA, _SCHEMA_SOLO_NOME, user_input)

    async def _passo_voce(
        self,
        tipo: str,
        schema: vol.Schema,
        user_input: dict[str, Any] | None,
        campo_data: str | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            dati: dict[str, Any] = {CONF_TIPO: tipo, **user_input}
            dati[CONF_NOME] = str(user_input.get(CONF_NOME, "")).strip()
            if not dati[CONF_NOME]:
                errors[CONF_NOME] = "campo_obbligatorio"
            if campo_data is not None:
                giorno = date.fromisoformat(str(user_input[campo_data]))
                if tipo == TIPO_VEICOLO:
                    giorno = giorno.replace(day=1)
                if giorno > dt_util.now().date():
                    errors[campo_data] = "data_futura"
                dati[campo_data] = giorno.isoformat()
            if not errors:
                self._dati_voce = dati
                return await self.async_step_scegli_scadenze()
        return self.async_show_form(
            step_id=tipo,
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
        )

    async def async_step_scegli_scadenze(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        tipo = self._dati_voce[CONF_TIPO]
        if user_input is not None:
            self._coda_modelli = list(user_input.get(CAMPO_MODELLI, []))
            self._scadenze_raccolte = []
            if not self._coda_modelli:
                return self._crea_entry()
            return await self.async_step_dettagli_scadenza()
        schema = vol.Schema(
            {
                vol.Optional(
                    CAMPO_MODELLI, default=modelli_raccomandati(tipo)
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=modelli_per_tipo(tipo),
                        multiple=True,
                        translation_key=CAMPO_MODELLO,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(step_id="scegli_scadenze", data_schema=schema)

    async def async_step_dettagli_scadenza(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        chiave = self._coda_modelli[0]
        voce = Voce.da_dict(self._dati_voce)
        oggi = dt_util.now().date()
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                scadenza = costruisci_scadenza(chiave, user_input, voce, oggi)
            except ErroreForm as err:
                errors[err.campo] = err.codice
            else:
                self._scadenze_raccolte.append(scadenza)
                self._coda_modelli.pop(0)
                if self._coda_modelli:
                    return await self.async_step_dettagli_scadenza()
                return self._crea_entry()
            valori: dict[str, Any] = user_input
        else:
            valori = valori_suggeriti(chiave, voce, oggi)

        return self.async_show_form(
            step_id="dettagli_scadenza",
            data_schema=self.add_suggested_values_to_schema(_schema_dettagli(chiave), valori),
            errors=errors,
            description_placeholders={"modello": MODELLI[chiave].etichetta},
        )

    def _crea_entry(self) -> ConfigFlowResult:
        subentries = [
            ConfigSubentryData(
                subentry_type=SUBENTRY_SCADENZA,
                title=scadenza.nome,
                unique_id=None,
                data=scadenza.a_dict(),
            )
            for scadenza in self._scadenze_raccolte
        ]
        return self.async_create_entry(
            title=self._dati_voce[CONF_NOME], data=self._dati_voce, subentries=subentries
        )


class ScadenzeOptionsFlow(OptionsFlow):
    """Sensore km (veicoli) e promemoria di una voce."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self.config_entry
        errors: dict[str, str] = {}
        if user_input is not None:
            opzioni = dict(user_input)
            try:
                opzioni[CONF_PREAVVISI] = analizza_preavvisi(str(user_input.get(CONF_PREAVVISI, "")))
            except PreavvisiNonValidi:
                errors[CONF_PREAVVISI] = "preavvisi_non_validi"
            servizio = str(user_input.get(CONF_SERVIZIO_NOTIFICA, "")).strip()
            opzioni[CONF_SERVIZIO_NOTIFICA] = servizio
            dominio, _, nome = servizio.partition(".")
            if user_input.get(CONF_NOTIFICHE_ATTIVE) and (
                not nome or not self.hass.services.has_service(dominio, nome)
            ):
                errors[CONF_SERVIZIO_NOTIFICA] = "servizio_non_trovato"
            if not errors:
                return self.async_create_entry(data=opzioni)
            valori = user_input
        else:
            valori = {
                CONF_NOTIFICHE_ATTIVE: True,
                CONF_SERVIZIO_NOTIFICA: PREDEFINITO_SERVIZIO_NOTIFICA,
                CONF_ORARIO_NOTIFICA: PREDEFINITO_ORARIO_NOTIFICA,
                **entry.options,
                CONF_PREAVVISI: formatta_preavvisi(entry.options.get(CONF_PREAVVISI, PREDEFINITO_PREAVVISI)),
            }
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                _schema_opzioni(entry.data.get(CONF_TIPO) == TIPO_VEICOLO), valori
            ),
            errors=errors,
        )


class ScadenzaSubentryFlow(ConfigSubentryFlow):
    """Aggiunge o riconfigura una scadenza di una voce."""

    def __init__(self) -> None:
        self._modello: str | None = None

    def _voce(self) -> Voce:
        return Voce.da_dict(self._get_entry().data)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        if user_input is not None:
            self._modello = user_input[CAMPO_MODELLO]
            return await self.async_step_dettagli()
        schema = vol.Schema(
            {
                vol.Required(CAMPO_MODELLO): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=modelli_per_tipo(self._voce().tipo),
                        translation_key=CAMPO_MODELLO,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        self._modello = self._get_reconfigure_subentry().data["modello"]
        return await self.async_step_dettagli()

    async def async_step_dettagli(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        assert self._modello is not None
        chiave = self._modello
        voce = self._voce()
        oggi = dt_util.now().date()
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                scadenza = costruisci_scadenza(chiave, user_input, voce, oggi)
            except ErroreForm as err:
                errors[err.campo] = err.codice
            else:
                if self.source == SOURCE_USER:
                    return self.async_create_entry(title=scadenza.nome, data=scadenza.a_dict())
                subentry = self._get_reconfigure_subentry()
                precedente = Scadenza.da_dict(subentry.data)
                if scadenza.ultimo_rinnovo is None:
                    scadenza = replace(scadenza, ultimo_rinnovo=precedente.ultimo_rinnovo)
                return self.async_update_and_abort(
                    self._get_entry(), subentry, title=scadenza.nome, data=scadenza.a_dict()
                )
            valori: dict[str, Any] = user_input
        elif self.source == SOURCE_USER:
            valori = valori_suggeriti(chiave, voce, oggi)
        else:
            valori = valori_da_scadenza(Scadenza.da_dict(self._get_reconfigure_subentry().data))

        return self.async_show_form(
            step_id="dettagli",
            data_schema=self.add_suggested_values_to_schema(_schema_dettagli(chiave), valori),
            errors=errors,
            description_placeholders={"modello": MODELLI[chiave].etichetta},
        )
