"""Broker factual performance report HTML artifact rendering — SLICE-0089.

Pure, side-effect-free rendering of the exact facts
`hullq.application.broker_performance_read.get_organization_performance_snapshot`
(or a stored PeriodRun's frozen snapshot) already decided, into a
self-contained, sanitized, printable/downloadable standalone HTML document
(Bounded one-screen broker UI section: "standalone sanitized HTML
(print-to-PDF supported by the browser) is the permitted low-cost
baseline"). Never fetches a remote resource, never embeds a script, never
re-derives/re-aggregates a count -- every number rendered here is exactly
what the caller supplied.

Used both for the live on-demand "Download report" route and for a stored
PeriodRun's historical artifact -- the identical renderer guarantees
"identical metrics to the browser" (truth contract) by construction: there
is only one code path from facts dict to report bytes.
"""

from __future__ import annotations

from html import escape
from typing import Any

__all__ = ["SUPPORTED_REPORT_LOCALES", "render_report_html"]

SUPPORTED_REPORT_LOCALES: tuple[str, ...] = ("en", "de", "fr", "pt", "es")

_DEFAULT_LOCALE = "en"

_TEXT: dict[str, dict[str, str]] = {
    "en": {
        "title": "HullQ Performance Report",
        "generated_at": "Report generated",
        "window": "Reporting period",
        "org_summary": "Organization summary",
        "views": "Public listing views observed",
        "leads_received": "Leads received",
        "leads_contacted": "Leads with a recorded broker contact attempt",
        "leads_closed": "Leads closed",
        "sold": "Explicit SOLD outcomes recorded in this period",
        "sold_known": "known source",
        "sold_unknown": "unknown source",
        "latency": "Median first-contact latency",
        "latency_unknown": "Not observed",
        "latency_population": "observed for {known} of {total} Leads",
        "acquisition": "Lead acquisition source breakdown",
        "discovery": "Lead discovery source breakdown",
        "listings": "Per-listing breakdown",
        "no_listings": "No observed views, Leads or recorded SOLD outcomes for this period.",
        "truncated": "Listing rows were truncated to a bounded maximum for this report.",
        "col_listing": "Listing",
        "col_views": "Views",
        "col_leads": "Leads received",
        "col_contacted": "Leads contacted",
        "col_closed": "Leads closed",
        "col_sold": "SOLD outcome",
        "not_recorded": "Not recorded",
    },
    "de": {
        "title": "HullQ Leistungsbericht",
        "generated_at": "Bericht erstellt",
        "window": "Berichtszeitraum",
        "org_summary": "Zusammenfassung der Organisation",
        "views": "Beobachtete öffentliche Angebotsaufrufe",
        "leads_received": "Erhaltene Leads",
        "leads_contacted": "Leads mit erfasstem Maklerkontaktversuch",
        "leads_closed": "Abgeschlossene Leads",
        "sold": "Explizite VERKAUFT-Ergebnisse in diesem Zeitraum",
        "sold_known": "bekannte Quelle",
        "sold_unknown": "unbekannte Quelle",
        "latency": "Mittlere Zeit bis zum Erstkontakt",
        "latency_unknown": "Nicht beobachtet",
        "latency_population": "beobachtet für {known} von {total} Leads",
        "acquisition": "Aufschlüsselung der Lead-Akquisequelle",
        "discovery": "Aufschlüsselung der Lead-Entdeckungsquelle",
        "listings": "Aufschlüsselung je Angebot",
        "no_listings": "Keine beobachteten Aufrufe, Leads oder VERKAUFT-Ergebnisse in diesem Zeitraum.",
        "truncated": "Angebotszeilen wurden für diesen Bericht auf ein begrenztes Maximum gekürzt.",
        "col_listing": "Angebot",
        "col_views": "Aufrufe",
        "col_leads": "Erhaltene Leads",
        "col_contacted": "Kontaktierte Leads",
        "col_closed": "Abgeschlossene Leads",
        "col_sold": "VERKAUFT-Ergebnis",
        "not_recorded": "Nicht erfasst",
    },
    "fr": {
        "title": "Rapport de performance HullQ",
        "generated_at": "Rapport généré",
        "window": "Période du rapport",
        "org_summary": "Résumé de l'organisation",
        "views": "Vues d'annonce publiques observées",
        "leads_received": "Prospects reçus",
        "leads_contacted": "Prospects avec une tentative de contact du courtier enregistrée",
        "leads_closed": "Prospects clôturés",
        "sold": "Résultats explicites VENDU enregistrés pour cette période",
        "sold_known": "source connue",
        "sold_unknown": "source inconnue",
        "latency": "Délai médian du premier contact",
        "latency_unknown": "Non observé",
        "latency_population": "observé pour {known} sur {total} prospects",
        "acquisition": "Répartition par source d'acquisition des prospects",
        "discovery": "Répartition par source de découverte des prospects",
        "listings": "Détail par annonce",
        "no_listings": "Aucune vue, prospect ou résultat VENDU observé pour cette période.",
        "truncated": "Les lignes d'annonces ont été tronquées à un maximum borné pour ce rapport.",
        "col_listing": "Annonce",
        "col_views": "Vues",
        "col_leads": "Prospects reçus",
        "col_contacted": "Prospects contactés",
        "col_closed": "Prospects clôturés",
        "col_sold": "Résultat VENDU",
        "not_recorded": "Non enregistré",
    },
    "pt": {
        "title": "Relatório de desempenho HullQ",
        "generated_at": "Relatório gerado",
        "window": "Período do relatório",
        "org_summary": "Resumo da organização",
        "views": "Visualizações públicas do anúncio observadas",
        "leads_received": "Leads recebidos",
        "leads_contacted": "Leads com tentativa de contato do corretor registrada",
        "leads_closed": "Leads encerrados",
        "sold": "Resultados explícitos de VENDIDO registrados neste período",
        "sold_known": "origem conhecida",
        "sold_unknown": "origem desconhecida",
        "latency": "Latência mediana do primeiro contato",
        "latency_unknown": "Não observado",
        "latency_population": "observado em {known} de {total} leads",
        "acquisition": "Distribuição por origem de aquisição dos leads",
        "discovery": "Distribuição por origem de descoberta dos leads",
        "listings": "Detalhamento por anúncio",
        "no_listings": "Nenhuma visualização, lead ou resultado VENDIDO observado neste período.",
        "truncated": "As linhas de anúncios foram truncadas para um máximo limitado neste relatório.",
        "col_listing": "Anúncio",
        "col_views": "Visualizações",
        "col_leads": "Leads recebidos",
        "col_contacted": "Leads contatados",
        "col_closed": "Leads encerrados",
        "col_sold": "Resultado VENDIDO",
        "not_recorded": "Não registrado",
    },
    "es": {
        "title": "Informe de rendimiento de HullQ",
        "generated_at": "Informe generado",
        "window": "Período del informe",
        "org_summary": "Resumen de la organización",
        "views": "Vistas públicas del anuncio observadas",
        "leads_received": "Leads recibidos",
        "leads_contacted": "Leads con intento de contacto del agente registrado",
        "leads_closed": "Leads cerrados",
        "sold": "Resultados explícitos de VENDIDO registrados en este período",
        "sold_known": "origen conocido",
        "sold_unknown": "origen desconocido",
        "latency": "Latencia mediana del primer contacto",
        "latency_unknown": "No observado",
        "latency_population": "observado en {known} de {total} leads",
        "acquisition": "Desglose por origen de adquisición de leads",
        "discovery": "Desglose por origen de descubrimiento de leads",
        "listings": "Desglose por anuncio",
        "no_listings": "No se observaron vistas, leads ni resultados VENDIDO en este período.",
        "truncated": "Las filas de anuncios se truncaron a un máximo acotado para este informe.",
        "col_listing": "Anuncio",
        "col_views": "Vistas",
        "col_leads": "Leads recibidos",
        "col_contacted": "Leads contactados",
        "col_closed": "Leads cerrados",
        "col_sold": "Resultado VENDIDO",
        "not_recorded": "No registrado",
    },
}


def _resolve_locale(locale: str | None) -> str:
    if locale is not None and locale in _TEXT:
        return locale
    return _DEFAULT_LOCALE


def _format_latency(seconds: float | None) -> str:
    if seconds is None:
        return ""
    hours = seconds / 3600
    if hours < 48:
        return f"{hours:.1f}h"
    return f"{hours / 24:.1f}d"


def render_report_html(
    *,
    organization_display_name: str,
    generated_at_iso: str,
    facts: dict[str, Any],
    locale: str | None = None,
) -> str:
    """Render *facts* (the exact shape of
    `OrganizationPerformanceFacts.to_public_dict()`, optionally with a
    `listings_truncated` key) into a standalone, self-contained HTML
    document. Every interpolated value is HTML-escaped; no remote
    resources, scripts or third-party content are ever embedded (Bounded
    one-screen broker UI section).
    """
    t = _TEXT[_resolve_locale(locale)]

    known = facts["first_contact_latency_known_count"]
    total = known + facts["first_contact_latency_unknown_count"]
    latency_text = _format_latency(facts["median_first_contact_latency_seconds"])
    latency_display = latency_text if latency_text else t["latency_unknown"]
    latency_population = t["latency_population"].format(known=known, total=total)

    acquisition_rows = "".join(
        f"<tr><td>{escape(str(channel))}</td><td>{escape(str(count))}</td></tr>"
        for channel, count in facts["acquisition_source_breakdown"].items()
    )
    discovery_rows = "".join(
        f"<tr><td>{escape(str(surface))}</td><td>{escape(str(count))}</td></tr>"
        for surface, count in facts["discovery_source_breakdown"].items()
    )

    listings = facts.get("listings", [])
    if listings:
        listing_rows = "".join(
            "<tr>"
            f"<td>{escape(str(listing['native_listing_id']))}</td>"
            f"<td>{escape(str(listing['public_listing_views']))}</td>"
            f"<td>{escape(str(listing['leads_received']))}</td>"
            f"<td>{escape(str(listing['leads_contacted']))}</td>"
            f"<td>{escape(str(listing['leads_closed']))}</td>"
            "<td>"
            + (
                t["not_recorded"]
                if listing["sold_outcome_recorded_at"] is None
                else (
                    f"{escape(str(listing['sold_outcome_recorded_at']))} "
                    f"({t['sold_known'] if listing['sold_outcome_source_known'] else t['sold_unknown']})"
                )
            )
            + "</td>"
            "</tr>"
            for listing in listings
        )
        listings_html = (
            f"<table><thead><tr><th>{escape(t['col_listing'])}</th>"
            f"<th>{escape(t['col_views'])}</th><th>{escape(t['col_leads'])}</th>"
            f"<th>{escape(t['col_contacted'])}</th><th>{escape(t['col_closed'])}</th>"
            f"<th>{escape(t['col_sold'])}</th></tr></thead>"
            f"<tbody>{listing_rows}</tbody></table>"
        )
        if facts.get("listings_truncated"):
            listings_html += f"<p class='notice'>{escape(t['truncated'])}</p>"
    else:
        listings_html = f"<p>{escape(t['no_listings'])}</p>"

    return f"""<!doctype html>
<html lang="{escape(_resolve_locale(locale))}">
<head>
<meta charset="utf-8">
<meta name="robots" content="noindex">
<title>{escape(t["title"])} — {escape(organization_display_name)}</title>
<style>
body {{ font-family: sans-serif; max-width: 860px; margin: 2rem auto; color: #111; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 1.5rem; }}
th, td {{ border: 1px solid #ccc; padding: 0.4rem 0.6rem; text-align: left; }}
h1, h2, h3 {{ margin-top: 1.5rem; }}
.notice {{ font-style: italic; }}
</style>
</head>
<body>
<h1>{escape(t["title"])} — {escape(organization_display_name)}</h1>
<p>{escape(t["generated_at"])}: {escape(generated_at_iso)}</p>
<p>{escape(t["window"])}: {escape(str(facts["window_start"]))} - {escape(str(facts["window_end"]))}</p>

<h2>{escape(t["org_summary"])}</h2>
<table>
<tr><td>{escape(t["views"])}</td><td>{escape(str(facts["public_listing_views"]))}</td></tr>
<tr><td>{escape(t["leads_received"])}</td><td>{escape(str(facts["leads_received"]))}</td></tr>
<tr><td>{escape(t["leads_contacted"])}</td><td>{escape(str(facts["leads_contacted"]))} / {escape(str(facts["leads_received"]))}</td></tr>
<tr><td>{escape(t["leads_closed"])}</td><td>{escape(str(facts["leads_closed"]))}</td></tr>
<tr><td>{escape(t["sold"])}</td><td>{escape(str(facts["sold_outcomes"]))} ({escape(str(facts["sold_outcomes_with_known_source"]))} {escape(t["sold_known"])} / {escape(str(facts["sold_outcomes_with_unknown_source"]))} {escape(t["sold_unknown"])})</td></tr>
<tr><td>{escape(t["latency"])}</td><td>{escape(latency_display)} ({escape(latency_population)})</td></tr>
</table>

<h3>{escape(t["acquisition"])}</h3>
<table><tbody>{acquisition_rows}</tbody></table>

<h3>{escape(t["discovery"])}</h3>
<table><tbody>{discovery_rows}</tbody></table>

<h2>{escape(t["listings"])}</h2>
{listings_html}
</body>
</html>
"""
