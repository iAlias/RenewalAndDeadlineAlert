"""Costanti condivise di Scadenze Auto & Casa.

Il modulo non importa Home Assistant: lo usano anche i moduli di logica pura.
"""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "scadenze"
SUBENTRY_SCADENZA: Final = "scadenza"
EVENTO_PROMEMORIA: Final = "scadenze_promemoria"

# Dati della voce (entry.data)
CONF_TIPO: Final = "tipo"
CONF_NOME: Final = "nome"
CONF_TIPO_VEICOLO: Final = "tipo_veicolo"
CONF_IMMATRICOLAZIONE: Final = "immatricolazione"
CONF_DATA_NASCITA: Final = "data_nascita"

TIPO_VEICOLO: Final = "veicolo"
TIPO_CASA: Final = "casa"
TIPO_PERSONA: Final = "persona"
TIPO_GENERICA: Final = "generica"
TIPI_VOCE: Final = (TIPO_VEICOLO, TIPO_CASA, TIPO_PERSONA, TIPO_GENERICA)

ETICHETTE_TIPO_VOCE: Final = {
    TIPO_VEICOLO: "Veicolo",
    TIPO_CASA: "Casa",
    TIPO_PERSONA: "Persona",
    TIPO_GENERICA: "Generica",
}

VEICOLO_AUTO: Final = "auto"
VEICOLO_MOTO: Final = "moto"

# Opzioni della voce (entry.options)
CONF_SENSORE_KM: Final = "sensore_km"
CONF_NOTIFICHE_ATTIVE: Final = "notifiche_attive"
CONF_SERVIZIO_NOTIFICA: Final = "servizio_notifica"
CONF_PREAVVISI: Final = "preavvisi"
CONF_ORARIO_NOTIFICA: Final = "orario_notifica"

PREDEFINITO_SERVIZIO_NOTIFICA: Final = "notify.persistent_notification"
PREDEFINITO_PREAVVISI: Final = (30, 7, 1)
PREDEFINITO_ORARIO_NOTIFICA: Final = "09:00:00"

FINESTRA_SENZA_PREAVVISI: Final = 30
SOGLIA_KM: Final = 1000
TOLLERANZA_ASSICURAZIONE_GIORNI: Final = 15

# Card Lovelace (fase 2)
URL_STATICO: Final = "/scadenze_static"
NOME_FILE_CARD: Final = "scadenze-card.js"
CHIAVE_FRONTEND_REGISTRATO: Final = f"{DOMAIN}_frontend_registrato"
