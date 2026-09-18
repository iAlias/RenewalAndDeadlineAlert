# Configurazione guidata e card con scadenze scelte — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** dopo aver creato una voce (veicolo/casa/persona/generica), guidare la creazione delle sue prime
scadenze in un unico flusso concatenato invece di richiedere un'azione separata per ciascuna; dare alla
card Lovelace una terza modalità che mostra solo scadenze scelte singolarmente, di qualunque voce.

**Architecture:** il `ConfigFlow` esistente si estende con due nuovi step (`scegli_scadenze`,
`dettagli_scadenza`) che riusano le funzioni pure già esistenti in `modelli.py`
(`modelli_per_tipo`, `valori_suggeriti`, `costruisci_scadenza`) e creano voce e scadenze insieme con
`async_create_entry(..., subentries=[...])`. La card riceve un nuovo campo `modalita`
(`tutte` | `voce` | `scelte`) che sceglie quale filtro applicare in `logica.js`; l'editor mostra solo i
campi della modalità attiva, costruiti dinamicamente invece che da uno schema fisso.

**Tech Stack:** Python 3.14 / Home Assistant custom component (config flow, subentries), JavaScript
(Web Component senza build, `ha-form`), `pytest` + `pytest-homeassistant-custom-component`, `node --test`.

**Spec:** `docs/superpowers/specs/2026-09-18-scadenze-onboarding-e-card-scelte-design.md`

## Global Constraints

- Home Assistant minimo 2026.8.0 (invariato).
- `tests/logica/` e `tests/card/*.test.mjs` girano anche su questa macchina Windows; `tests/ha/` gira solo
  in CI (GitHub Actions, Ubuntu) — su Windows `homeassistant.runner` non si avvia (vedi
  `docs/superpowers/specs/2026-09-14-scadenze-auto-casa-design.md` §16.3). Ogni step che tocca `tests/ha`
  lo dice esplicitamente invece di dare un comando da eseguire in locale.
- Card: Node 22, nessuna dipendenza npm (`node --test "tests/card/*.test.mjs"`).
- Le etichette dei modelli e delle scadenze restano in italiano fisso dove già lo sono oggi (nomi di
  dispositivo, valori predefiniti); form, selettori e testi della card restano tradotti `it`/`en`.
- Non toccare le regole di calcolo (`regole.py`), il modello dati (`modello_dati.py`) o il coordinator:
  fuori perimetro per questo lavoro.

---

## Task 1: `modelli_raccomandati` — i modelli preselezionati per tipo di voce

**Files:**
- Modify: `custom_components/scadenze/modelli.py`
- Test: `tests/logica/test_modelli.py`

**Interfaces:**
- Consumes: `MODELLI`, `M_PERSONALIZZATA` (già importati in `modelli.py`), `modelli_per_tipo` (già definita
  nello stesso file).
- Produces: `CAMPO_MODELLI: Final[str] = "modelli"` e `modelli_raccomandati(tipo_voce: str) -> list[str]`,
  entrambi esportati da `custom_components/scadenze/modelli.py`. Il Task 2 li importa così com'è.

- [ ] **Step 1: Scrivi il test che fallisce**

Aggiungi in fondo a `tests/logica/test_modelli.py` (il file importa già `Voce` e le costanti dei tipi; non
serve altro import oltre a quello aggiunto nello Step successivo):

```python
def test_modelli_raccomandati_esclude_personalizzata() -> None:
    assert modelli_raccomandati("veicolo") == [
        "revisione", "bollo", "assicurazione", "tagliando", "gomme",
    ]
    assert modelli_raccomandati("casa") == [
        "manutenzione_caldaia",
        "controllo_fumi",
        "climatizzatore",
        "estintore",
        "filtri_acqua",
        "canna_fumaria",
    ]
    assert modelli_raccomandati("persona") == [
        "carta_identita", "patente", "passaporto", "tessera_sanitaria",
    ]
    assert modelli_raccomandati("generica") == []
```

Aggiungi `modelli_raccomandati` all'import da `custom_components.scadenze.modelli` in cima al file (riga 10-18).

- [ ] **Step 2: Esegui il test e verifica che fallisca**

Run: `python -m pytest tests/logica/test_modelli.py::test_modelli_raccomandati_esclude_personalizzata -v`
Expected: FAIL con `ImportError: cannot import name 'modelli_raccomandati'`

- [ ] **Step 3: Implementa**

In `custom_components/scadenze/modelli.py`, aggiungi la costante subito dopo `CAMPO_RICORRENZA` (riga 63) e
aggiungila a `CAMPI_NOTI` NO — `CAMPI_NOTI` è l'insieme dei campi di un *modello* (usati nei form per
scadenza), `modelli` è il campo del nuovo step del flusso principale e non fa parte di quell'insieme: non
toccare `CAMPI_NOTI`.

```python
CAMPO_RICORRENZA: Final = "ricorrenza"
CAMPO_MODELLI: Final = "modelli"
```

Aggiungi la funzione subito dopo `modelli_per_tipo` (dopo la riga 154):

```python
def modelli_raccomandati(tipo_voce: str) -> list[str]:
    """I modelli preselezionati per un tipo di voce: tutti tranne «personalizzata»."""
    return [chiave for chiave in modelli_per_tipo(tipo_voce) if chiave != M_PERSONALIZZATA]
```

- [ ] **Step 4: Esegui il test e verifica che passi**

Run: `python -m pytest tests/logica/test_modelli.py -v`
Expected: PASS (tutti i test del file, non solo quello nuovo)

- [ ] **Step 5: Commit**

```bash
git add custom_components/scadenze/modelli.py tests/logica/test_modelli.py
git commit -m "feat: modelli_raccomandati, i modelli preselezionati per tipo di voce"
```

---

## Task 2: Wizard a catena nel flusso di configurazione

**Files:**
- Modify: `custom_components/scadenze/config_flow.py`
- Modify: `custom_components/scadenze/strings.json`
- Modify: `custom_components/scadenze/translations/en.json`
- Modify: `custom_components/scadenze/translations/it.json`
- Test: `tests/ha/test_config_flow.py`

**Interfaces:**
- Consumes: `CAMPO_MODELLI`, `modelli_raccomandati` (Task 1); `modelli_per_tipo`, `valori_suggeriti`,
  `costruisci_scadenza`, `MODELLI`, `ErroreForm`, `_schema_dettagli` (già in `config_flow.py`);
  `homeassistant.config_entries.ConfigSubentryData` (stesso modulo da cui già si importa
  `ConfigSubentryFlow`; usata anche da `tests/ha/common.py` nella forma `ConfigSubentryDataWithId`, quindi
  è nello stesso modulo).
- Produces: nessuna nuova interfaccia pubblica; cambia il comportamento di `ScadenzeConfigFlow` (vedi
  sotto). Il Task 5 non dipende da nulla di nuovo qui.

Questo task tocca `tests/ha/`: **i suoi test non sono eseguibili in locale su questa macchina Windows**
(`homeassistant.runner` richiede `fcntl`). Si verificano solo dopo il push, nel job `test` della CI
(`.github/workflows/validate.yml`). Scrivi comunque il test prima del codice: è la stessa disciplina, solo
che il "run e verifica che fallisca/passi" diventa "verifica sul run di CI dopo il push", annotato negli
step dove serve.

- [ ] **Step 1: Aggiorna le stringhe (serve al form prima ancora di poterlo testare)**

In `custom_components/scadenze/strings.json`, dentro `"config"."step"`, aggiungi due nuovi step dopo
`"generica"` (riga 45, prima della chiusura di `"step"`):

```json
      "generica": {
        "title": "New item",
        "data": {
          "nome": "Name"
        }
      },
      "scegli_scadenze": {
        "title": "Which deadlines?",
        "description": "Add them now, with suggested values where possible. You can add more later from the item's device page.",
        "data": {
          "modelli": "Deadlines to add now"
        }
      },
      "dettagli_scadenza": {
        "title": "{modello}",
        "data": {
          "nome": "Name",
          "scadenza": "Due date",
          "mese_scadenza_bollo": "Month the road tax expires",
          "ultimo_rinnovo": "Last done on",
          "intervallo_mesi": "Every how many months",
          "km_ultimo_rinnovo": "Kilometres at the last service",
          "intervallo_km": "Every how many kilometres",
          "ricorrenza": "Repeats"
        },
        "data_description": {
          "scadenza": "Suggested dates come from the rules: check them against your documents.",
          "mese_scadenza_bollo": "The expiry month on the last receipt. Payment is due by the end of the following month.",
          "intervallo_km": "0 disables the kilometre limit."
        }
      }
```

E in `"config"."error"` (riga 47-50), aggiungi i codici che `costruisci_scadenza` può sollevare e che oggi
mancano in questa sezione (ci sono già in `config_subentries.scadenza.error`, servono anche qui perché il
nuovo step `dettagli_scadenza` vive sotto `config`, non sotto `config_subentries`):

```json
    "error": {
      "campo_obbligatorio": "This field is required.",
      "data_non_valida": "This date is not valid.",
      "data_futura": "The date cannot be in the future.",
      "intervallo_non_valido": "The value is out of range.",
      "scadenza_prima_della_nascita": "The due date is before the date of birth."
    }
```

Ripeti **esattamente le stesse chiavi** in `custom_components/scadenze/translations/en.json` (identico a
`strings.json` in questo repo, verificato all'inizio del task) con lo stesso testo inglese.

In `custom_components/scadenze/translations/it.json`, stessa struttura con questo testo:

```json
      "scegli_scadenze": {
        "title": "Quali scadenze?",
        "description": "Aggiungile ora, con i valori suggeriti dove possibile. Puoi aggiungerne altre più tardi dalla pagina del dispositivo della voce.",
        "data": {
          "modelli": "Scadenze da aggiungere ora"
        }
      },
      "dettagli_scadenza": {
        "title": "{modello}",
        "data": {
          "nome": "Nome",
          "scadenza": "Data di scadenza",
          "mese_scadenza_bollo": "Mese di scadenza del bollo",
          "ultimo_rinnovo": "Ultima volta il",
          "intervallo_mesi": "Ogni quanti mesi",
          "km_ultimo_rinnovo": "Chilometri all'ultimo tagliando",
          "intervallo_km": "Ogni quanti chilometri",
          "ricorrenza": "Si ripete"
        },
        "data_description": {
          "scadenza": "Le date suggerite vengono dalle regole: controllale con i tuoi documenti.",
          "mese_scadenza_bollo": "Il mese di scadenza sull'ultima ricevuta. Si paga entro la fine del mese successivo.",
          "intervallo_km": "0 disattiva il limite in chilometri."
        }
      }
```

```json
    "error": {
      "campo_obbligatorio": "Questo campo è obbligatorio.",
      "data_non_valida": "Questa data non è valida.",
      "data_futura": "La data non può essere nel futuro.",
      "intervallo_non_valido": "Il valore è fuori dall'intervallo ammesso.",
      "scadenza_prima_della_nascita": "La scadenza è precedente alla data di nascita."
    }
```

Verifica che i tre file JSON siano validi: `python -m json.tool custom_components/scadenze/strings.json`,
ripeti per gli altri due (deve stampare il JSON senza errori).

- [ ] **Step 2: Scrivi i test del wizard che falliscono**

In `tests/ha/test_config_flow.py`, sostituisci `test_nuovo_veicolo` con questa versione (ora passa per il
nuovo step con `modelli: []`, quindi crea solo la voce come prima):

```python
async def test_nuovo_veicolo(hass: HomeAssistant) -> None:
    form = await avvia_voce(hass, "veicolo")
    assert (form["type"], form["step_id"]) == (FlowResultType.FORM, "veicolo")

    scelta = await hass.config_entries.flow.async_configure(
        form["flow_id"], {"nome": "Panda", "tipo_veicolo": "auto", "immatricolazione": "2022-05-18"}
    )
    assert scelta["step_id"] == "scegli_scadenze"

    risultato = await hass.config_entries.flow.async_configure(scelta["flow_id"], {"modelli": []})

    assert risultato["type"] is FlowResultType.CREATE_ENTRY
    assert risultato["title"] == "Panda"
    assert risultato["data"] == {
        "tipo": "veicolo",
        "nome": "Panda",
        "tipo_veicolo": "auto",
        "immatricolazione": "2022-05-01",
    }
    assert risultato["result"].subentries == {}
```

Sostituisci `test_nuova_persona_casa_e_generica` con:

```python
async def test_nuova_persona_casa_e_generica(hass: HomeAssistant) -> None:
    form = await avvia_voce(hass, "persona")
    scelta = await hass.config_entries.flow.async_configure(
        form["flow_id"], {"nome": "Mario", "data_nascita": "1990-05-08"}
    )
    persona = await hass.config_entries.flow.async_configure(scelta["flow_id"], {"modelli": []})
    assert persona["data"] == {"tipo": "persona", "nome": "Mario", "data_nascita": "1990-05-08"}

    for tipo, nome in (("casa", "Casa al mare"), ("generica", "Abbonamenti")):
        form = await avvia_voce(hass, tipo)
        scelta = await hass.config_entries.flow.async_configure(form["flow_id"], {"nome": nome})
        risultato = await hass.config_entries.flow.async_configure(scelta["flow_id"], {"modelli": []})
        assert risultato["data"] == {"tipo": tipo, "nome": nome}
```

Sostituisci `test_una_voce_generica_offre_solo_la_personalizzata` con:

```python
async def test_una_voce_generica_offre_solo_la_personalizzata(hass: HomeAssistant) -> None:
    form = await avvia_voce(hass, "generica")
    scelta = await hass.config_entries.flow.async_configure(form["flow_id"], {"nome": "Abbonamenti"})
    assert opzioni_selettore(scelta, "modelli") == ["personalizzata"]
    creata = await hass.config_entries.flow.async_configure(scelta["flow_id"], {"modelli": []})
    await hass.async_block_till_done()

    scelta_sub = await hass.config_entries.subentries.async_init(
        (creata["result"].entry_id, "scadenza"), context={"source": SOURCE_USER}
    )
    assert opzioni_selettore(scelta_sub, "modello") == ["personalizzata"]
```

`test_immatricolazione_futura` non cambia (fallisce prima di arrivare al nuovo step).

Aggiungi questi tre nuovi test dopo `test_immatricolazione_futura`:

```python
async def test_wizard_usa_i_modelli_raccomandati_di_default(hass: HomeAssistant) -> None:
    form = await avvia_voce(hass, "veicolo")
    scelta = await hass.config_entries.flow.async_configure(
        form["flow_id"], {"nome": "Panda", "tipo_veicolo": "auto", "immatricolazione": "2022-05-01"}
    )
    assert scelta["step_id"] == "scegli_scadenze"

    # Nessun valore inviato: si applica il default dello schema (tutti tranne "personalizzata"),
    # quindi il flusso passa alla prima scadenza raccomandata invece di creare subito la entry.
    primo = await hass.config_entries.flow.async_configure(scelta["flow_id"], {})
    assert primo["step_id"] == "dettagli_scadenza"
    assert primo["description_placeholders"] == {"modello": "Revisione"}


async def test_wizard_crea_voce_e_scadenze_scelte_insieme(hass: HomeAssistant) -> None:
    form = await avvia_voce(hass, "veicolo")
    scelta = await hass.config_entries.flow.async_configure(
        form["flow_id"], {"nome": "Panda", "tipo_veicolo": "auto", "immatricolazione": "2022-05-18"}
    )
    assert opzioni_selettore(scelta, "modelli") == [
        "revisione", "bollo", "assicurazione", "tagliando", "gomme", "personalizzata",
    ]

    revisione = await hass.config_entries.flow.async_configure(
        scelta["flow_id"], {"modelli": ["revisione", "bollo"]}
    )
    assert revisione["step_id"] == "dettagli_scadenza"
    assert revisione["description_placeholders"] == {"modello": "Revisione"}
    assert suggerito(revisione, "scadenza") == "2028-05-31"

    bollo = await hass.config_entries.flow.async_configure(
        revisione["flow_id"], {"nome": "Revisione", "scadenza": "2028-05-31"}
    )
    assert bollo["step_id"] == "dettagli_scadenza"
    assert bollo["description_placeholders"] == {"modello": "Bollo"}
    assert suggerito(bollo, "mese_scadenza_bollo") == "2027-04-01"

    risultato = await hass.config_entries.flow.async_configure(
        bollo["flow_id"], {"nome": "Bollo", "mese_scadenza_bollo": "2027-04-01"}
    )
    await hass.async_block_till_done()

    assert risultato["type"] is FlowResultType.CREATE_ENTRY
    entry = risultato["result"]
    assert {sub.title for sub in entry.subentries.values()} == {"Revisione", "Bollo"}
    assert {sub.data["regola"] for sub in entry.subentries.values()} == {"fine_mese"}


async def test_wizard_errore_non_perde_le_scadenze_gia_confermate(hass: HomeAssistant) -> None:
    form = await avvia_voce(hass, "veicolo")
    scelta = await hass.config_entries.flow.async_configure(
        form["flow_id"], {"nome": "Panda", "tipo_veicolo": "auto", "immatricolazione": "2022-05-18"}
    )
    revisione = await hass.config_entries.flow.async_configure(
        scelta["flow_id"], {"modelli": ["revisione", "tagliando"]}
    )
    tagliando = await hass.config_entries.flow.async_configure(
        revisione["flow_id"], {"nome": "Revisione", "scadenza": "2028-05-31"}
    )
    assert tagliando["description_placeholders"] == {"modello": "Tagliando"}

    errore = await hass.config_entries.flow.async_configure(
        tagliando["flow_id"],
        {
            "nome": "Tagliando",
            "ultimo_rinnovo": "2026-09-15",
            "km_ultimo_rinnovo": 0,
            "intervallo_mesi": 12,
            "intervallo_km": 15000,
        },
    )
    assert errore["errors"] == {"ultimo_rinnovo": "data_futura"}
    assert errore["step_id"] == "dettagli_scadenza"
    assert errore["description_placeholders"] == {"modello": "Tagliando"}

    risultato = await hass.config_entries.flow.async_configure(
        errore["flow_id"],
        {
            "nome": "Tagliando",
            "ultimo_rinnovo": "2026-09-01",
            "km_ultimo_rinnovo": 30000,
            "intervallo_mesi": 12,
            "intervallo_km": 15000,
        },
    )
    await hass.async_block_till_done()

    assert risultato["type"] is FlowResultType.CREATE_ENTRY
    assert {sub.title for sub in risultato["result"].subentries.values()} == {"Revisione", "Tagliando"}
```

I due valori `"2028-05-31"` e `"2027-04-01"` sono calcolati da `prossima_revisione_da_immatricolazione` e
`mese_scadenza_bollo_suggerito` (`custom_components/scadenze/regole.py`) con immatricolazione
`2022-05-01` (il giorno si normalizza sempre a 1, vedi `_passo_voce`) e "oggi" `2026-09-14` (fissato da
`tests/ha/conftest.py`). Se cambi la data di immatricolazione nel test, ricalcola questi due valori a mano
prima di scriverli.

Non eseguire ancora questi test: `homeassistant` non è installato su questa macchina (serve `fcntl`).
Passa direttamente all'implementazione.

- [ ] **Step 3: Implementa il wizard**

In `custom_components/scadenze/config_flow.py`, modifica l'import da `homeassistant.config_entries`
(righe 11-19) aggiungendo `ConfigSubentryData`:

```python
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
```

Modifica l'import da `.modelli` (righe 48-65) aggiungendo `CAMPO_MODELLI` e `modelli_raccomandati`:

```python
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
```

Sostituisci l'intera classe `ScadenzeConfigFlow` (righe 117-192 del file originale) con:

```python
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
```

Il resto del file (`ScadenzeOptionsFlow`, `ScadenzaSubentryFlow`) non cambia.

- [ ] **Step 4: Verifica la sintassi in locale, poi affida il resto alla CI**

Run: `python -m py_compile custom_components/scadenze/config_flow.py`
Expected: nessun output (compila senza errori)

Poi esegui in locale solo i test che non toccano `homeassistant`, per assicurarti di non aver rotto nulla
di puro:

Run: `python -m pytest tests/logica -q`
Expected: PASS

I test di `tests/ha/test_config_flow.py` (compresi i tre nuovi e i tre modificati in questo step) restano
da verificare sulla CI dopo il push del Task 2 — annotalo nel messaggio del commit o nel PR.

- [ ] **Step 5: Commit**

```bash
git add custom_components/scadenze/config_flow.py custom_components/scadenze/strings.json \
  custom_components/scadenze/translations/en.json custom_components/scadenze/translations/it.json \
  tests/ha/test_config_flow.py
git commit -m "feat: wizard a catena, crea voce e scadenze scelte in un solo flusso"
```

---

## Task 3: La card riconosce la modalità «scelte» (logica pura)

**Files:**
- Modify: `custom_components/scadenze/frontend/logica.js`
- Test: `tests/card/logica.test.mjs`

**Interfaces:**
- Consumes: nessuna nuova dipendenza esterna al file.
- Produces: `OPZIONI_PREDEFINITE` con due chiavi in più (`modalita: ""`, `scelte: []`); `filtraEOrdina`
  legge anche queste due chiavi. Il Task 4 (editor) si aspetta esattamente questi nomi di campo.

- [ ] **Step 1: Scrivi i test che falliscono**

In `tests/card/logica.test.mjs`, sostituisci il test `"configurazione con valori predefiniti"` (righe
151-163) con:

```javascript
test("configurazione con valori predefiniti", () => {
  assert.deepEqual(normalizzaConfig({ titolo: "Casa" }), {
    titolo: "Casa",
    voce: "",
    modalita: "",
    scelte: [],
    nascondi_ok: false,
    mostra_giorni: true,
    mostra_km: true,
    mostra_rinnovato: true,
  });
  for (const sbagliata of [null, [], "scadenze"]) {
    assert.throws(() => normalizzaConfig(sbagliata));
  }
});
```

Aggiungi questi due test dopo `"filtra per voce e nasconde le scadenze ok"` (dopo la riga 111):

```javascript
test("modalita scelte mostra solo le scadenze indicate, in qualunque ordine di selezione", () => {
  const scadenze = raccogliScadenze(hassDiProva());
  assert.deepEqual(
    filtraEOrdina(scadenze, { modalita: "scelte", scelte: ["dev_tag", "dev_bollo"] }).map((s) => s.id),
    ["dev_bollo", "dev_tag"],
  );
  assert.deepEqual(filtraEOrdina(scadenze, { modalita: "scelte", scelte: [] }).map((s) => s.id), []);
});

test("senza modalita si comporta come prima: voce se impostata, altrimenti tutte", () => {
  const scadenze = raccogliScadenze(hassDiProva());
  assert.deepEqual(
    filtraEOrdina(scadenze, { voce: "entry_mario" }).map((s) => s.id),
    filtraEOrdina(scadenze, { modalita: "voce", voce: "entry_mario" }).map((s) => s.id),
  );
  assert.deepEqual(
    filtraEOrdina(scadenze, {}).map((s) => s.id),
    filtraEOrdina(scadenze, { modalita: "tutte" }).map((s) => s.id),
  );
});
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

Run: `node --test "tests/card/logica.test.mjs"`
Expected: FAIL su `"configurazione con valori predefiniti"` (mancano `modalita`/`scelte`) e su
`"modalita scelte mostra solo le scadenze indicate..."` (nessun filtro applicato: la modalità non esiste
ancora)

- [ ] **Step 3: Implementa**

In `custom_components/scadenze/frontend/logica.js`, modifica `OPZIONI_PREDEFINITE` (righe 5-12):

```javascript
export const OPZIONI_PREDEFINITE = Object.freeze({
  titolo: "",
  voce: "",
  modalita: "",
  scelte: [],
  nascondi_ok: false,
  mostra_giorni: true,
  mostra_km: true,
  mostra_rinnovato: true,
});
```

Sostituisci `filtraEOrdina` (righe 104-115):

```javascript
export function filtraEOrdina(scadenze, config) {
  const opzioni = normalizzaConfig(config);
  const modalita = opzioni.modalita || (opzioni.voce ? "voce" : "tutte");
  return scadenze
    .filter((s) => modalita !== "voce" || s.voceId === opzioni.voce)
    .filter((s) => modalita !== "scelte" || opzioni.scelte.includes(s.id))
    .filter((s) => !opzioni.nascondi_ok || STATI_VISIBILI_SE_NASCONDI_OK.has(s.stato))
    .sort((a, b) => {
      const gruppo = (GRUPPO_ORDINE[a.stato] ?? 3) - (GRUPPO_ORDINE[b.stato] ?? 3);
      if (gruppo !== 0) return gruppo;
      const data = (a.data ?? "9999-99-99").localeCompare(b.data ?? "9999-99-99");
      return data !== 0 ? data : a.nome.localeCompare(b.nome);
    });
}
```

- [ ] **Step 4: Esegui i test e verifica che passino**

Run: `node --test "tests/card/logica.test.mjs"`
Expected: PASS (tutti i test del file)

- [ ] **Step 5: Commit**

```bash
git add custom_components/scadenze/frontend/logica.js tests/card/logica.test.mjs
git commit -m "feat: filtro modalita/scelte nella logica della card"
```

---

## Task 4: L'editor della card mostra solo i campi della modalità scelta

**Files:**
- Modify: `custom_components/scadenze/frontend/scadenze-card.js`
- Test: `tests/card/card.test.mjs`

**Interfaces:**
- Consumes: `OPZIONI_PREDEFINITE`/`filtraEOrdina` con `modalita`/`scelte` (Task 3); `raccogliScadenze`,
  `normalizzaConfig`, `lingua` (già importati in cima al file).
- Produces: nessuna nuova interfaccia pubblica; cambia `SCHEMA_EDITOR` (statico) in `schemaEditor(...)`
  (funzione).

- [ ] **Step 1: Scrivi il test che fallisce**

In `tests/card/card.test.mjs`, sostituisci il test `"l'editor emette la configurazione senza voce e
titolo vuoti"` (righe 150-185) con:

```javascript
test("l'editor mostra i campi giusti per ogni modalita e pulisce la configurazione", () => {
  const editor = document.createElement("scadenze-card-editor");
  const ricevute = [];
  editor.addEventListener("config-changed", (evento) => ricevute.push(evento.detail.config));
  editor.setConfig({ type: "custom:scadenze-card" });
  editor.hass = hassDiProva();

  let form = editor.figli[0];
  assert.equal(form.data.mostra_giorni, true);
  assert.equal(form.data.modalita, "tutte");
  assert.ok(!form.schema.some((campo) => campo.name === "voce"));
  assert.ok(!form.schema.some((campo) => campo.name === "scelte"));

  form.dispatchEvent({ type: "value-changed", detail: { value: { ...form.data, modalita: "voce" } } });
  editor.setConfig(ricevute.at(-1));
  form = editor.figli[0];
  assert.equal(
    form.schema.find((campo) => campo.name === "voce").selector.config_entry.integration,
    "scadenze",
  );
  assert.ok(!form.schema.some((campo) => campo.name === "scelte"));

  form.dispatchEvent({
    type: "value-changed",
    detail: { value: { ...form.data, modalita: "scelte", voce: "" } },
  });
  editor.setConfig(ricevute.at(-1));
  form = editor.figli[0];
  const campoScelte = form.schema.find((campo) => campo.name === "scelte");
  assert.deepEqual(
    campoScelte.selector.select.options.map((o) => o.value).sort(),
    ["dev_cie", "dev_rev"],
  );
  assert.ok(!form.schema.some((campo) => campo.name === "voce"));

  form.dispatchEvent({
    type: "value-changed",
    detail: { value: { ...form.data, nascondi_ok: true, scelte: [] } },
  });
  assert.deepEqual(ricevute.at(-1), {
    type: "custom:scadenze-card",
    modalita: "scelte",
    nascondi_ok: true,
    mostra_giorni: true,
    mostra_km: true,
    mostra_rinnovato: true,
  });
});
```

- [ ] **Step 2: Esegui il test e verifica che fallisca**

Run: `node --test "tests/card/card.test.mjs"`
Expected: FAIL (`form.data.modalita` è `undefined`, non esiste ancora `campo.name === "modalita"` né un
campo `scelte` con `selector.select.options`)

- [ ] **Step 3: Implementa**

In `custom_components/scadenze/frontend/scadenze-card.js`, sostituisci il blocco `SCHEMA_EDITOR` /
`ETICHETTE_EDITOR` (righe 166-192) con:

```javascript
const ETICHETTE_MODALITA = {
  it: { tutte: "Tutte", voce: "Una voce", scelte: "Scelgo io" },
  en: { tutte: "All", voce: "One item", scelte: "I choose" },
};

function schemaEditor(codice, modalita, scadenze) {
  const campi = [
    { name: "titolo", selector: { text: {} } },
    {
      name: "modalita",
      selector: {
        select: {
          mode: "dropdown",
          options: ["tutte", "voce", "scelte"].map((valore) => ({
            value: valore,
            label: ETICHETTE_MODALITA[codice][valore],
          })),
        },
      },
    },
  ];
  if (modalita === "voce") {
    campi.push({ name: "voce", selector: { config_entry: { integration: "scadenze" } } });
  }
  if (modalita === "scelte") {
    campi.push({
      name: "scelte",
      selector: {
        select: {
          multiple: true,
          mode: "list",
          options: scadenze.map((s) => ({
            value: s.id,
            label: s.voce ? `${s.nome} — ${s.voce}` : s.nome,
          })),
        },
      },
    });
  }
  campi.push(
    { name: "nascondi_ok", selector: { boolean: {} } },
    { name: "mostra_giorni", selector: { boolean: {} } },
    { name: "mostra_km", selector: { boolean: {} } },
    { name: "mostra_rinnovato", selector: { boolean: {} } },
  );
  return campi;
}

const ETICHETTE_EDITOR = {
  it: {
    titolo: "Titolo",
    modalita: "Cosa mostrare",
    voce: "Voce",
    scelte: "Scadenze da mostrare",
    nascondi_ok: "Nascondi le scadenze in regola",
    mostra_giorni: "Mostra i giorni mancanti",
    mostra_km: "Mostra i km mancanti",
    mostra_rinnovato: "Mostra il pulsante Rinnovato",
  },
  en: {
    titolo: "Title",
    modalita: "What to show",
    voce: "Item",
    scelte: "Deadlines to show",
    nascondi_ok: "Hide deadlines that are fine",
    mostra_giorni: "Show days left",
    mostra_km: "Show kilometres left",
    mostra_rinnovato: "Show the Renewed button",
  },
};
```

Sostituisci la classe `ScadenzeCardEditor` (righe 194-231):

```javascript
class ScadenzeCardEditor extends HTMLElement {
  constructor() {
    super();
    this._config = {};
    this._hass = null;
    this._form = null;
  }

  setConfig(config) {
    this._config = { ...config };
    this._aggiorna();
  }

  set hass(hass) {
    this._hass = hass;
    this._aggiorna();
  }

  _aggiorna() {
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (campo) => ETICHETTE_EDITOR[lingua(this._hass)][campo.name] ?? campo.name;
      this._form.addEventListener("value-changed", (evento) => this._cambiata(evento.detail.value));
      this.appendChild(this._form);
    }
    const dati = normalizzaConfig(this._config);
    dati.modalita = dati.modalita || "tutte";
    const scadenze = this._hass ? raccogliScadenze(this._hass) : [];
    this._form.hass = this._hass;
    this._form.schema = schemaEditor(lingua(this._hass), dati.modalita, scadenze);
    this._form.data = dati;
  }

  _cambiata(valore) {
    const config = { ...valore };
    if (!config.titolo) delete config.titolo;
    if (!config.voce) delete config.voce;
    if (!config.scelte || !config.scelte.length) delete config.scelte;
    this._config = config;
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }));
  }
}
```

Il resto del file (classe `ScadenzeCard`, registrazione dei custom element, `window.customCards`) non
cambia.

- [ ] **Step 4: Esegui i test e verifica che passino**

Run: `node --test "tests/card/*.test.mjs"`
Expected: PASS (tutti i test di `logica.test.mjs` e `card.test.mjs`)

- [ ] **Step 5: Commit**

```bash
git add custom_components/scadenze/frontend/scadenze-card.js tests/card/card.test.mjs
git commit -m "feat: editor della card con campi condizionali per modalita"
```

---

## Task 5: Versione e documentazione

**Files:**
- Modify: `custom_components/scadenze/manifest.json`
- Modify: `README.md`

**Interfaces:**
- Consumes: nessuna.
- Produces: nessuna (ultimo task).

- [ ] **Step 1: Aggiorna la versione**

In `custom_components/scadenze/manifest.json`, cambia `"version": "0.2.0"` in `"version": "0.3.0"`.

- [ ] **Step 2: Aggiorna la sezione «Come si usa» del README**

In `README.md`, sostituisci i punti 1-2 di `## Come si usa` (righe 29-30):

```markdown
1. **Crea una voce**: un veicolo (con il mese di prima immatricolazione), una casa, una persona (con la data di nascita) o una voce generica.
2. Scegli quali scadenze aggiungere subito (revisione, bollo, assicurazione...): il flusso ti guida una alla volta, con i valori suggeriti già compilati dove possibile. Puoi sempre aggiungerne altre più tardi dalla pagina del dispositivo della voce, con **Aggiungi scadenza**.
```

Il punto 3 (opzioni/notifiche) resta invariato.

- [ ] **Step 3: Aggiorna la sezione «La card»**

In `README.md`, sostituisci il blocco YAML di esempio (righe 92-100):

```markdown
```yaml
type: custom:scadenze-card
titolo: Scadenze
modalita: tutte           # tutte (predefinito) | voce | scelte
voce: <voce>               # con modalita: voce
scelte:                    # con modalita: scelte
  - <scadenza 1>
  - <scadenza 2>
nascondi_ok: false
mostra_giorni: true
mostra_km: true
mostra_rinnovato: true
```
```

E la tabella delle opzioni (righe 102-109), aggiungendo `modalita` e `scelte` subito dopo `titolo`:

```markdown
| Opzione | Predefinito | Cosa fa |
|---|---|---|
| `titolo` | nessuno | Intestazione della card |
| `modalita` | `tutte` | `tutte`, `voce` (una voce sola) o `scelte` (scadenze scelte a mano, di qualunque voce) |
| `voce` | — | Con `modalita: voce`, quale voce mostrare |
| `scelte` | — | Con `modalita: scelte`, quali scadenze mostrare |
| `nascondi_ok` | `false` | Mostra solo le scadenze superate o vicine |
| `mostra_giorni` | `true` | Aggiunge «tra N giorni» o «scaduta da N giorni» |
| `mostra_km` | `true` | Aggiunge i km mancanti al tagliando |
| `mostra_rinnovato` | `true` | Pulsante «Rinnovato»: il primo clic chiede conferma, il secondo rinnova |
```

- [ ] **Step 4: Verifica**

Run: `python -m json.tool custom_components/scadenze/manifest.json`
Expected: nessun output (JSON valido)

Rileggi le sezioni modificate del README a occhio: nessun riferimento rimasto al vecchio comportamento
("Sulla scheda della voce premi Aggiungi scadenza" come primo passo, vecchia tabella senza `modalita`).

- [ ] **Step 5: Commit**

```bash
git add custom_components/scadenze/manifest.json README.md
git commit -m "chore: versione 0.3.0, README aggiornato per wizard e modalita della card"
```

---

## Dopo l'implementazione

Push del branch e apertura di una PR (CI: `hassfest`, `test`, `card`; `hacs` gira solo sul branch
predefinito). I tre test nuovi/modificati in `tests/ha/test_config_flow.py` (Task 2) vanno verificati sul
run di CI, non prima: è l'unico modo per eseguirli su questa macchina.
