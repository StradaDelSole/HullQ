// SLICE-0059: localized presentation text for the anonymous factual
// shortlist Compare surface (`/{locale}/shortlist/compare`,
// `specs/ANONYMOUS_FACTUAL_SHORTLIST_COMPARE_CONTRACT.v0.1.md`). Only the
// text that is genuinely new to Compare lives here -- unavailable/service
// wording, price-on-application, freshness labels, view-listing text and the
// Save/Saved/Remove labels are already localized in `./shortlistText.ts` and
// are reused verbatim by `shortlistCompareRuntime.ts` rather than duplicated
// or reworded here, so the two surfaces never drift.
//
// Contract §6/§8: this file's job is presentation wording only. It must
// never collapse VALUE_ASSERTION/UNKNOWN/not-supplied into one another, and
// it must never introduce winner/best-fit/recommended/score language.

import type { SupportedLocale } from "./shortlistText";

export interface ShortlistCompareText {
  pageTitle: string;
  pageHeading: string;
  noscriptMessage: string;
  loadingMessage: string;
  /** Zero saved ids (contract §3). */
  emptyMessage: string;
  /** Exactly one saved id (contract §3). */
  needOneMoreMessage: string;
  /** The resolver request itself failed (contract §9/§13), page-level. */
  serviceErrorMessage: string;
  compareLinkLabel: string;
  backToShortlistLabel: string;
  identityFallbackLabel: string;
  priceLabel: string;
  locationLabel: string;
  buildYearLabel: string;
  loaLabel: string;
  draftLabel: string;
  keelLabel: string;
  rudderLabel: string;
  freshnessLabel: string;
  /**
   * Independent review 2026-09-19 (PR #221): `last_confirmed_at` must be
   * unambiguously labeled as the *last confirmed* timestamp -- on a DUE row,
   * a bare `(<timestamp>)` next to the DUE status can otherwise read as a
   * due-by date. This label is prefixed onto that timestamp in every
   * locale.
   */
  lastConfirmedLabel: string;
  /** Broker declared an explicit UNKNOWN for a bounded PhysicalBoat claim field. */
  unknownLabel: string;
  /** The broker never supplied this bounded PhysicalBoat claim field at all. */
  notSuppliedLabel: string;
}

export const shortlistCompareText: Record<SupportedLocale, ShortlistCompareText> = {
  en: {
    pageTitle: "Compare your shortlist",
    pageHeading: "Compare your shortlist",
    noscriptMessage: "Compare needs JavaScript enabled in your browser.",
    loadingMessage: "Loading your comparison…",
    emptyMessage: "Your shortlist is empty. Save at least two listings to compare them.",
    needOneMoreMessage: "Save at least one more listing to compare.",
    serviceErrorMessage:
      "We couldn't load current comparison details right now. Your saved listings are unaffected; please try again in a moment.",
    compareLinkLabel: "Compare shortlist",
    backToShortlistLabel: "Back to your shortlist",
    identityFallbackLabel: "Listing",
    priceLabel: "Asking price",
    locationLabel: "Location",
    buildYearLabel: "Build year",
    loaLabel: "LOA",
    draftLabel: "Draft",
    keelLabel: "Keel configuration",
    rudderLabel: "Rudder configuration",
    freshnessLabel: "Freshness",
    lastConfirmedLabel: "Last confirmed",
    unknownLabel: "Unknown",
    notSuppliedLabel: "Not supplied",
  },
  de: {
    pageTitle: "Merkliste vergleichen",
    pageHeading: "Merkliste vergleichen",
    noscriptMessage: "Für den Vergleich muss JavaScript in Ihrem Browser aktiviert sein.",
    loadingMessage: "Vergleich wird geladen…",
    emptyMessage:
      "Ihre Merkliste ist leer. Speichern Sie mindestens zwei Angebote, um sie zu vergleichen.",
    needOneMoreMessage: "Speichern Sie mindestens ein weiteres Angebot, um zu vergleichen.",
    serviceErrorMessage:
      "Aktuelle Vergleichsdetails konnten gerade nicht geladen werden. Ihre gespeicherten Angebote sind davon nicht betroffen; bitte versuchen Sie es in Kürze erneut.",
    compareLinkLabel: "Merkliste vergleichen",
    backToShortlistLabel: "Zurück zu Ihrer Merkliste",
    identityFallbackLabel: "Angebot",
    priceLabel: "Preisvorstellung",
    locationLabel: "Standort",
    buildYearLabel: "Baujahr",
    loaLabel: "Länge über alles",
    draftLabel: "Tiefgang",
    keelLabel: "Kielkonfiguration",
    rudderLabel: "Ruderkonfiguration",
    freshnessLabel: "Aktualität",
    lastConfirmedLabel: "Zuletzt bestätigt",
    unknownLabel: "Unbekannt",
    notSuppliedLabel: "Nicht angegeben",
  },
  fr: {
    pageTitle: "Comparer votre liste de favoris",
    pageHeading: "Comparer votre liste de favoris",
    noscriptMessage: "La comparaison nécessite que JavaScript soit activé dans votre navigateur.",
    loadingMessage: "Chargement de la comparaison…",
    emptyMessage:
      "Votre liste de favoris est vide. Enregistrez au moins deux annonces pour les comparer.",
    needOneMoreMessage: "Enregistrez au moins une annonce supplémentaire pour comparer.",
    serviceErrorMessage:
      "Nous n'avons pas pu charger les détails de comparaison actuels pour le moment. Vos annonces enregistrées ne sont pas affectées ; veuillez réessayer dans un instant.",
    compareLinkLabel: "Comparer la liste de favoris",
    backToShortlistLabel: "Retour à votre liste de favoris",
    identityFallbackLabel: "Annonce",
    priceLabel: "Prix demandé",
    locationLabel: "Localisation",
    buildYearLabel: "Année de construction",
    loaLabel: "Longueur hors tout",
    draftLabel: "Tirant d'eau",
    keelLabel: "Configuration de quille",
    rudderLabel: "Configuration du gouvernail",
    freshnessLabel: "Actualité",
    lastConfirmedLabel: "Dernière confirmation",
    unknownLabel: "Inconnu",
    notSuppliedLabel: "Non fourni",
  },
  pt: {
    pageTitle: "Comparar a sua lista de interesses",
    pageHeading: "Comparar a sua lista de interesses",
    noscriptMessage: "A comparação requer JavaScript ativado no seu navegador.",
    loadingMessage: "A carregar a comparação…",
    emptyMessage:
      "A sua lista de interesses está vazia. Guarde pelo menos dois anúncios para os comparar.",
    needOneMoreMessage: "Guarde pelo menos mais um anúncio para comparar.",
    serviceErrorMessage:
      "Não foi possível carregar os detalhes de comparação atuais neste momento. Os seus anúncios guardados não são afetados; tente novamente dentro de instantes.",
    compareLinkLabel: "Comparar lista de interesses",
    backToShortlistLabel: "Voltar à sua lista de interesses",
    identityFallbackLabel: "Anúncio",
    priceLabel: "Preço pedido",
    locationLabel: "Localização",
    buildYearLabel: "Ano de construção",
    loaLabel: "Comprimento fora a fora",
    draftLabel: "Calado",
    keelLabel: "Configuração da quilha",
    rudderLabel: "Configuração do leme",
    freshnessLabel: "Atualidade",
    lastConfirmedLabel: "Última confirmação",
    unknownLabel: "Desconhecido",
    notSuppliedLabel: "Não fornecido",
  },
  es: {
    pageTitle: "Comparar su lista de interés",
    pageHeading: "Comparar su lista de interés",
    noscriptMessage: "La comparación requiere JavaScript activado en su navegador.",
    loadingMessage: "Cargando la comparación…",
    emptyMessage: "Su lista de interés está vacía. Guarde al menos dos anuncios para compararlos.",
    needOneMoreMessage: "Guarde al menos un anuncio más para comparar.",
    serviceErrorMessage:
      "No hemos podido cargar los detalles de comparación actuales en este momento. Sus anuncios guardados no se ven afectados; inténtelo de nuevo en unos instantes.",
    compareLinkLabel: "Comparar lista de interés",
    backToShortlistLabel: "Volver a su lista de interés",
    identityFallbackLabel: "Anuncio",
    priceLabel: "Precio solicitado",
    locationLabel: "Ubicación",
    buildYearLabel: "Año de construcción",
    loaLabel: "Eslora total",
    draftLabel: "Calado",
    keelLabel: "Configuración de quilla",
    rudderLabel: "Configuración del timón",
    freshnessLabel: "Actualidad",
    lastConfirmedLabel: "Última confirmación",
    unknownLabel: "Desconocido",
    notSuppliedLabel: "No facilitado",
  },
};
