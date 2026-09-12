// SLICE-0051: localized presentation text for the bounded draft_max Search
// surface (item K — technical parameter names, ids, Decimal meaning,
// provenance and Search semantics stay language-neutral; only this prose is
// translated). Covers Required Behavior §I in full for every locale: what
// requirement was applied, why a confirmed boat qualifies, what concrete
// draft HullQ used, that the value is broker-declared unless separately
// verified, whether evidence is missing/conflicting, why insufficient
// evidence is not called a match, and what action is available next.

export type SupportedLocale = "en" | "de" | "fr" | "pt" | "es";

export const SUPPORTED_LOCALES: readonly SupportedLocale[] = ["en", "de", "fr", "pt", "es"];

export interface SearchText {
  title: string;
  draftMaxLabel: string;
  draftMaxPlaceholder: string;
  submit: string;
  formInstructions: string;
  invalidTitle: string;
  invalidFallback: string;
  startOver: string;
  serviceUnavailableTitle: string;
  serviceUnavailableMessage: string;
  requirementSummary: (draftMax: string) => string;
  confirmedHeading: string;
  noConfirmedMatches: string;
  resolvedDraftText: (resolvedDraftM: string) => string;
  insufficientDataText: (count: number) => string;
  viewListing: string;
}

export const searchText: Record<SupportedLocale, SearchText> = {
  en: {
    title: "Search: maximum draft",
    draftMaxLabel: "Maximum draft (metres)",
    draftMaxPlaceholder: "1.6",
    submit: "Search",
    formInstructions:
      "Enter the deepest draft your boat can be, in metres. HullQ only shows boats a broker has confirmed meet this limit.",
    invalidTitle: "This search link isn't valid",
    invalidFallback: "Enter a maximum draft as a plain decimal number of metres, for example 1.6.",
    startOver: "Start a new search",
    serviceUnavailableTitle: "Search is temporarily unavailable",
    serviceUnavailableMessage:
      "We couldn't complete this search right now. Please try again in a moment.",
    requirementSummary: (draftMax) => `Showing boats confirmed to have a draft of ${draftMax} m or less.`,
    confirmedHeading: "Confirmed matches",
    noConfirmedMatches:
      "No listing currently has broker-confirmed evidence that its draft meets this requirement.",
    resolvedDraftText: (resolvedDraftM) =>
      `broker-declared draft: ${resolvedDraftM} m (not independently verified)`,
    insufficientDataText: (count) =>
      `${count} additional listing(s) could satisfy this requirement but are not shown as a match: the broker's draft is missing, unknown, or conflicts with another organization's current statement.`,
    viewListing: "View listing",
  },
  de: {
    title: "Suche: maximaler Tiefgang",
    draftMaxLabel: "Maximaler Tiefgang (Meter)",
    draftMaxPlaceholder: "1.6",
    submit: "Suchen",
    formInstructions:
      "Geben Sie den größten zulässigen Tiefgang in Metern an. HullQ zeigt nur Boote, deren Tiefgang von einem Makler innerhalb dieser Grenze bestätigt wurde.",
    invalidTitle: "Dieser Suchlink ist ungültig",
    invalidFallback:
      "Geben Sie den maximalen Tiefgang als einfache Dezimalzahl in Metern an, zum Beispiel 1.6.",
    startOver: "Neue Suche beginnen",
    serviceUnavailableTitle: "Die Suche ist vorübergehend nicht verfügbar",
    serviceUnavailableMessage:
      "Diese Suche konnte gerade nicht durchgeführt werden. Bitte versuchen Sie es in Kürze erneut.",
    requirementSummary: (draftMax) => `Boote mit bestätigtem Tiefgang von ${draftMax} m oder weniger.`,
    confirmedHeading: "Bestätigte Treffer",
    noConfirmedMatches:
      "Für kein Angebot liegt derzeit eine maklerbestätigte Bestätigung vor, dass der Tiefgang diese Anforderung erfüllt.",
    resolvedDraftText: (resolvedDraftM) =>
      `vom Makler angegebener Tiefgang: ${resolvedDraftM} m (nicht unabhängig verifiziert)`,
    insufficientDataText: (count) =>
      `${count} weitere(s) Angebot(e) könnten diese Anforderung erfüllen, werden aber nicht als Treffer angezeigt: Der Tiefgang fehlt, ist unbekannt oder widerspricht der aktuellen Angabe einer anderen Organisation.`,
    viewListing: "Angebot ansehen",
  },
  fr: {
    title: "Recherche : tirant d'eau maximal",
    draftMaxLabel: "Tirant d'eau maximal (mètres)",
    draftMaxPlaceholder: "1.6",
    submit: "Rechercher",
    formInstructions:
      "Indiquez le tirant d'eau maximal admissible, en mètres. HullQ n'affiche que les bateaux dont le courtier a confirmé qu'ils respectent cette limite.",
    invalidTitle: "Ce lien de recherche n'est pas valide",
    invalidFallback:
      "Indiquez le tirant d'eau maximal sous forme de nombre décimal simple en mètres, par exemple 1.6.",
    startOver: "Commencer une nouvelle recherche",
    serviceUnavailableTitle: "La recherche est temporairement indisponible",
    serviceUnavailableMessage:
      "Nous n'avons pas pu effectuer cette recherche pour le moment. Veuillez réessayer dans un instant.",
    requirementSummary: (draftMax) => `Bateaux dont le tirant d'eau confirmé est de ${draftMax} m ou moins.`,
    confirmedHeading: "Résultats confirmés",
    noConfirmedMatches:
      "Aucune annonce ne dispose actuellement d'une confirmation du courtier attestant que son tirant d'eau respecte cette exigence.",
    resolvedDraftText: (resolvedDraftM) =>
      `tirant d'eau déclaré par le courtier : ${resolvedDraftM} m (non vérifié de manière indépendante)`,
    insufficientDataText: (count) =>
      `${count} annonce(s) supplémentaire(s) pourraient satisfaire cette exigence mais ne sont pas affichées comme correspondance : le tirant d'eau est manquant, inconnu, ou contredit la déclaration actuelle d'une autre organisation.`,
    viewListing: "Voir l'annonce",
  },
  pt: {
    title: "Pesquisa: calado máximo",
    draftMaxLabel: "Calado máximo (metros)",
    draftMaxPlaceholder: "1.6",
    submit: "Pesquisar",
    formInstructions:
      "Indique o calado máximo admissível, em metros. A HullQ apenas apresenta barcos cujo corretor confirmou cumprirem este limite.",
    invalidTitle: "Esta ligação de pesquisa não é válida",
    invalidFallback:
      "Indique o calado máximo como um número decimal simples em metros, por exemplo 1.6.",
    startOver: "Iniciar nova pesquisa",
    serviceUnavailableTitle: "A pesquisa está temporariamente indisponível",
    serviceUnavailableMessage:
      "Não foi possível concluir esta pesquisa neste momento. Tente novamente dentro de instantes.",
    requirementSummary: (draftMax) => `A mostrar barcos com calado confirmado de ${draftMax} m ou menos.`,
    confirmedHeading: "Correspondências confirmadas",
    noConfirmedMatches:
      "Nenhum anúncio tem atualmente confirmação do corretor de que o calado cumpre este requisito.",
    resolvedDraftText: (resolvedDraftM) =>
      `calado declarado pelo corretor: ${resolvedDraftM} m (não verificado de forma independente)`,
    insufficientDataText: (count) =>
      `${count} anúncio(s) adicional(is) poderiam satisfazer este requisito mas não são apresentados como correspondência: o calado está em falta, é desconhecido, ou entra em conflito com a declaração atual de outra organização.`,
    viewListing: "Ver anúncio",
  },
  es: {
    title: "Búsqueda: calado máximo",
    draftMaxLabel: "Calado máximo (metros)",
    draftMaxPlaceholder: "1.6",
    submit: "Buscar",
    formInstructions:
      "Indique el calado máximo admisible, en metros. HullQ solo muestra barcos cuyo bróker ha confirmado que cumplen este límite.",
    invalidTitle: "Este enlace de búsqueda no es válido",
    invalidFallback:
      "Indique el calado máximo como un número decimal simple en metros, por ejemplo 1.6.",
    startOver: "Iniciar una nueva búsqueda",
    serviceUnavailableTitle: "La búsqueda no está disponible temporalmente",
    serviceUnavailableMessage:
      "No hemos podido completar esta búsqueda en este momento. Inténtelo de nuevo en unos instantes.",
    requirementSummary: (draftMax) => `Mostrando barcos con calado confirmado de ${draftMax} m o menos.`,
    confirmedHeading: "Coincidencias confirmadas",
    noConfirmedMatches:
      "Ningún anuncio cuenta actualmente con confirmación del bróker de que su calado cumple este requisito.",
    resolvedDraftText: (resolvedDraftM) =>
      `calado declarado por el bróker: ${resolvedDraftM} m (no verificado de forma independiente)`,
    insufficientDataText: (count) =>
      `${count} anuncio(s) adicional(es) podrían cumplir este requisito pero no se muestran como coincidencia: falta el calado, es desconocido, o entra en conflicto con la declaración actual de otra organización.`,
    viewListing: "Ver anuncio",
  },
};
