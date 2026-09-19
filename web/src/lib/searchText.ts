// SLICE-0051: localized presentation text for the bounded draft_max Search
// surface (item K — technical parameter names, ids, Decimal meaning,
// provenance and Search semantics stay language-neutral; only this prose is
// translated). Covers Required Behavior §I in full for every locale: what
// requirement was applied, why a confirmed boat qualifies, what concrete
// draft HullQ used, that the value is broker-declared unless separately
// verified, whether evidence is missing/conflicting, why insufficient
// evidence is not called a match, and what action is available next.
//
// SLICE-0056: extends the same coverage to the accepted `keel_configuration`
// criterion, alone or combined with `draft_max`. `keelConfigurationValues`
// (the six accepted technical tokens, `web/src/lib/searchApi.ts`'s
// `SEARCH_KEEL_CONFIGURATION_VALUES`) stay language-neutral; only their
// display labels below are translated.

export type SupportedLocale = "en" | "de" | "fr" | "pt" | "es";

export const SUPPORTED_LOCALES: readonly SupportedLocale[] = ["en", "de", "fr", "pt", "es"];

export interface SearchText {
  title: string;
  draftMaxLabel: string;
  draftMaxPlaceholder: string;
  keelConfigurationLabel: string;
  keelConfigurationAnyOption: string;
  /** Localized display label for each accepted technical keel value. */
  keelConfigurationLabels: {
    FIN: string;
    FIN_WITH_BULB: string;
    WING: string;
    CENTERBOARD: string;
    LIFTING_KEEL: string;
    TWIN_KEEL: string;
  };
  submit: string;
  formInstructions: string;
  invalidTitle: string;
  invalidFallback: string;
  startOver: string;
  serviceUnavailableTitle: string;
  serviceUnavailableMessage: string;
  requirementSummary: (draftMax: string) => string;
  /** SLICE-0056 keel-only active requirement (Required Behavior §C). */
  requirementSummaryKeelOnly: (keelLabel: string) => string;
  /** SLICE-0056 draft+keel active requirement. */
  requirementSummaryMixed: (draftMax: string, keelLabel: string) => string;
  confirmedHeading: string;
  noConfirmedMatches: string;
  /**
   * SLICE-0056: the same "no confirmed matches" state for a keel-only/mixed
   * requirement -- `noConfirmedMatches` itself is left verbatim (Required
   * Behavior §D/AC4: draft-only rendering stays byte-for-byte unchanged)
   * since its wording specifically names "draft".
   */
  noConfirmedMatchesGeneric: string;
  resolvedDraftText: (resolvedDraftM: string) => string;
  /** SLICE-0056 concrete keel evidence on a confirmed keel/mixed match. */
  resolvedKeelText: (keelLabel: string) => string;
  insufficientDataText: (count: number) => string;
  /**
   * SLICE-0056: category-level insufficient-data explanation for a keel/mixed
   * requirement (Required Behavior §E) — never names a specific listing's
   * missing field, mirroring `insufficientDataText`'s draft-only wording.
   */
  insufficientDataTextGeneric: (count: number) => string;
  viewListing: string;
  /** SLICE-0052: badge/label text distinguishing CONFIRMED from DUE_FOR_CONFIRMATION. */
  freshnessConfirmedLabel: string;
  freshnessDueLabel: string;
  /** MUST NOT word a DUE match as if it were simply "confirmed" (contract §H). */
  freshnessDueNote: string;

  // SLICE-0057: buyer-requirement-sensitivity text. Factual and
  // decision-neutral throughout (contract §12/§19) -- never "recommended",
  // "better", "worse", "optimal", "should" or "relax this".
  /** Shown alongside each per-active-criterion sensitivity form on the Search page. */
  sensitivityFormNote: string;
  sensitivityDraftSubmitLabel: string;
  sensitivityKeelSubmitLabel: string;
  sensitivityAlternativeDraftLabel: string;
  sensitivityAlternativeKeelLabel: string;
  sensitivityPageTitle: string;
  sensitivityCurrentHeading: string;
  sensitivityAlternativeHeading: string;
  sensitivityCurrentConfirmedLabel: (count: number) => string;
  sensitivityAlternativeConfirmedLabel: (count: number) => string;
  sensitivityNewlyConfirmedLabel: (count: number) => string;
  sensitivityNoLongerConfirmedLabel: (count: number) => string;
  sensitivityCurrentInsufficientLabel: (count: number) => string;
  sensitivityAlternativeInsufficientLabel: (count: number) => string;
  sensitivityViewAlternativeSearch: string;
  sensitivityInvalidTitle: string;
  sensitivityInvalidFallback: string;
  sensitivityServiceUnavailableTitle: string;
  sensitivityServiceUnavailableMessage: string;
  /** Shown for a direct GET to the POST-only sensitivity page (contract §13). */
  sensitivityMethodNotAllowedTitle: string;
  sensitivityMethodNotAllowedMessage: string;
}

export const searchText: Record<SupportedLocale, SearchText> = {
  en: {
    title: "Search: maximum draft",
    draftMaxLabel: "Maximum draft (metres)",
    draftMaxPlaceholder: "1.6",
    keelConfigurationLabel: "Keel configuration",
    keelConfigurationAnyOption: "Any keel configuration",
    keelConfigurationLabels: {
      FIN: "Fin keel",
      FIN_WITH_BULB: "Fin keel with bulb",
      WING: "Wing keel",
      CENTERBOARD: "Centerboard keel",
      LIFTING_KEEL: "Lifting keel",
      TWIN_KEEL: "Twin keel",
    },
    submit: "Search",
    formInstructions:
      "Enter the deepest draft your boat can be, in metres, and/or choose a keel configuration. HullQ only shows boats a broker has confirmed meet these requirements.",
    invalidTitle: "This search link isn't valid",
    invalidFallback:
      "Enter a maximum draft as a plain decimal number of metres (for example 1.6) and/or choose a supported keel configuration.",
    startOver: "Start a new search",
    serviceUnavailableTitle: "Search is temporarily unavailable",
    serviceUnavailableMessage:
      "We couldn't complete this search right now. Please try again in a moment.",
    requirementSummary: (draftMax) => `Showing boats confirmed to have a draft of ${draftMax} m or less.`,
    requirementSummaryKeelOnly: (keelLabel) => `Showing boats confirmed to have a ${keelLabel}.`,
    requirementSummaryMixed: (draftMax, keelLabel) =>
      `Showing boats confirmed to have a draft of ${draftMax} m or less and a ${keelLabel}.`,
    confirmedHeading: "Confirmed matches",
    noConfirmedMatches:
      "No listing currently has broker-confirmed evidence that its draft meets this requirement.",
    noConfirmedMatchesGeneric:
      "No listing currently has broker-confirmed evidence that it meets this requirement.",
    resolvedDraftText: (resolvedDraftM) =>
      `broker-declared draft: ${resolvedDraftM} m (not independently verified)`,
    resolvedKeelText: (keelLabel) =>
      `broker-declared keel configuration: ${keelLabel} (not independently verified)`,
    insufficientDataText: (count) =>
      `${count} additional listing(s) could satisfy this requirement but are not shown as a match: the broker's draft is missing, unknown, or conflicts with another organization's current statement.`,
    insufficientDataTextGeneric: (count) =>
      `${count} additional listing(s) could satisfy this requirement but are not shown as a match: the broker's evidence is missing, unknown, or conflicts with another organization's current statement.`,
    viewListing: "View listing",
    freshnessConfirmedLabel: "Confirmed current",
    freshnessDueLabel: "Reconfirmation due",
    freshnessDueNote:
      "The broker has not reconfirmed this listing recently; it will be hidden soon unless reconfirmed.",
    sensitivityFormNote:
      "See how many confirmed matches change if you try a different value for one requirement. This does not change your current search.",
    sensitivityDraftSubmitLabel: "See the effect of a different maximum draft",
    sensitivityKeelSubmitLabel: "See the effect of a different keel configuration",
    sensitivityAlternativeDraftLabel: "Alternative maximum draft (metres)",
    sensitivityAlternativeKeelLabel: "Alternative keel configuration",
    sensitivityPageTitle: "Requirement sensitivity",
    sensitivityCurrentHeading: "Current requirement",
    sensitivityAlternativeHeading: "Alternative requirement",
    sensitivityCurrentConfirmedLabel: (count) => `Currently confirmed matches: ${count}`,
    sensitivityAlternativeConfirmedLabel: (count) =>
      `Confirmed matches with the alternative: ${count}`,
    sensitivityNewlyConfirmedLabel: (count) => `${count} newly confirmed with the alternative`,
    sensitivityNoLongerConfirmedLabel: (count) =>
      `${count} no longer confirmed with the alternative`,
    sensitivityCurrentInsufficientLabel: (count) =>
      `${count} additional listing(s) have insufficient evidence under the current requirement`,
    sensitivityAlternativeInsufficientLabel: (count) =>
      `${count} additional listing(s) have insufficient evidence under the alternative requirement`,
    sensitivityViewAlternativeSearch: "View this search",
    sensitivityInvalidTitle: "This sensitivity request isn't valid",
    sensitivityInvalidFallback:
      "Choose one currently active requirement and supply one replacement value for it.",
    sensitivityServiceUnavailableTitle: "Sensitivity is temporarily unavailable",
    sensitivityServiceUnavailableMessage:
      "We couldn't complete this comparison right now. Please try again in a moment.",
    sensitivityMethodNotAllowedTitle: "Start from a search",
    sensitivityMethodNotAllowedMessage:
      "This page only shows a result after you submit a requirement change from the search page.",
  },
  de: {
    title: "Suche: maximaler Tiefgang",
    draftMaxLabel: "Maximaler Tiefgang (Meter)",
    draftMaxPlaceholder: "1.6",
    keelConfigurationLabel: "Kielkonfiguration",
    keelConfigurationAnyOption: "Beliebige Kielkonfiguration",
    keelConfigurationLabels: {
      FIN: "Finnenkiel",
      FIN_WITH_BULB: "Finnenkiel mit Bulbe",
      WING: "Flügelkiel",
      CENTERBOARD: "Schwertkiel",
      LIFTING_KEEL: "Hubkiel",
      TWIN_KEEL: "Doppelkiel",
    },
    submit: "Suchen",
    formInstructions:
      "Geben Sie den größten zulässigen Tiefgang in Metern an und/oder wählen Sie eine Kielkonfiguration. HullQ zeigt nur Boote, die von einem Makler als diesen Anforderungen entsprechend bestätigt wurden.",
    invalidTitle: "Dieser Suchlink ist ungültig",
    invalidFallback:
      "Geben Sie den maximalen Tiefgang als einfache Dezimalzahl in Metern an (zum Beispiel 1.6) und/oder wählen Sie eine unterstützte Kielkonfiguration.",
    startOver: "Neue Suche beginnen",
    serviceUnavailableTitle: "Die Suche ist vorübergehend nicht verfügbar",
    serviceUnavailableMessage:
      "Diese Suche konnte gerade nicht durchgeführt werden. Bitte versuchen Sie es in Kürze erneut.",
    requirementSummary: (draftMax) => `Boote mit bestätigtem Tiefgang von ${draftMax} m oder weniger.`,
    requirementSummaryKeelOnly: (keelLabel) => `Boote mit bestätigter Kielkonfiguration: ${keelLabel}.`,
    requirementSummaryMixed: (draftMax, keelLabel) =>
      `Boote mit bestätigtem Tiefgang von ${draftMax} m oder weniger und Kielkonfiguration: ${keelLabel}.`,
    confirmedHeading: "Bestätigte Treffer",
    noConfirmedMatches:
      "Für kein Angebot liegt derzeit eine maklerbestätigte Bestätigung vor, dass der Tiefgang diese Anforderung erfüllt.",
    noConfirmedMatchesGeneric:
      "Für kein Angebot liegt derzeit eine maklerbestätigte Bestätigung vor, dass es diese Anforderung erfüllt.",
    resolvedDraftText: (resolvedDraftM) =>
      `vom Makler angegebener Tiefgang: ${resolvedDraftM} m (nicht unabhängig verifiziert)`,
    resolvedKeelText: (keelLabel) =>
      `vom Makler angegebene Kielkonfiguration: ${keelLabel} (nicht unabhängig verifiziert)`,
    insufficientDataText: (count) =>
      `${count} weitere(s) Angebot(e) könnten diese Anforderung erfüllen, werden aber nicht als Treffer angezeigt: Der Tiefgang fehlt, ist unbekannt oder widerspricht der aktuellen Angabe einer anderen Organisation.`,
    insufficientDataTextGeneric: (count) =>
      `${count} weitere(s) Angebot(e) könnten diese Anforderung erfüllen, werden aber nicht als Treffer angezeigt: Die Angaben des Maklers fehlen, sind unbekannt oder widersprechen der aktuellen Angabe einer anderen Organisation.`,
    viewListing: "Angebot ansehen",
    freshnessConfirmedLabel: "Aktuell bestätigt",
    freshnessDueLabel: "Bestätigung ausstehend",
    freshnessDueNote:
      "Der Makler hat dieses Angebot kürzlich nicht erneut bestätigt; es wird bald ausgeblendet, sofern es nicht erneut bestätigt wird.",
    sensitivityFormNote:
      "Sehen Sie, wie viele bestätigte Treffer sich ändern, wenn Sie für eine Anforderung einen anderen Wert ausprobieren. Dies ändert Ihre aktuelle Suche nicht.",
    sensitivityDraftSubmitLabel: "Auswirkung eines anderen maximalen Tiefgangs anzeigen",
    sensitivityKeelSubmitLabel: "Auswirkung einer anderen Kielkonfiguration anzeigen",
    sensitivityAlternativeDraftLabel: "Alternativer maximaler Tiefgang (Meter)",
    sensitivityAlternativeKeelLabel: "Alternative Kielkonfiguration",
    sensitivityPageTitle: "Anforderungssensitivität",
    sensitivityCurrentHeading: "Aktuelle Anforderung",
    sensitivityAlternativeHeading: "Alternative Anforderung",
    sensitivityCurrentConfirmedLabel: (count) => `Aktuell bestätigte Treffer: ${count}`,
    sensitivityAlternativeConfirmedLabel: (count) =>
      `Bestätigte Treffer mit der Alternative: ${count}`,
    sensitivityNewlyConfirmedLabel: (count) => `${count} neu bestätigt mit der Alternative`,
    sensitivityNoLongerConfirmedLabel: (count) =>
      `${count} nicht mehr bestätigt mit der Alternative`,
    sensitivityCurrentInsufficientLabel: (count) =>
      `${count} weitere(s) Angebot(e) haben unter der aktuellen Anforderung unzureichende Nachweise`,
    sensitivityAlternativeInsufficientLabel: (count) =>
      `${count} weitere(s) Angebot(e) haben unter der alternativen Anforderung unzureichende Nachweise`,
    sensitivityViewAlternativeSearch: "Diese Suche ansehen",
    sensitivityInvalidTitle: "Diese Sensitivitätsanfrage ist ungültig",
    sensitivityInvalidFallback:
      "Wählen Sie eine derzeit aktive Anforderung und geben Sie dafür einen Ersatzwert an.",
    sensitivityServiceUnavailableTitle: "Die Sensitivitätsanalyse ist vorübergehend nicht verfügbar",
    sensitivityServiceUnavailableMessage:
      "Dieser Vergleich konnte gerade nicht durchgeführt werden. Bitte versuchen Sie es in Kürze erneut.",
    sensitivityMethodNotAllowedTitle: "Von einer Suche aus starten",
    sensitivityMethodNotAllowedMessage:
      "Diese Seite zeigt ein Ergebnis erst, nachdem Sie über die Suchseite eine Anforderungsänderung gesendet haben.",
  },
  fr: {
    title: "Recherche : tirant d'eau maximal",
    draftMaxLabel: "Tirant d'eau maximal (mètres)",
    draftMaxPlaceholder: "1.6",
    keelConfigurationLabel: "Configuration de quille",
    keelConfigurationAnyOption: "Toute configuration de quille",
    keelConfigurationLabels: {
      FIN: "Quille fine",
      FIN_WITH_BULB: "Quille fine à bulbe",
      WING: "Quille à ailettes",
      CENTERBOARD: "Dérive",
      LIFTING_KEEL: "Quille relevable",
      TWIN_KEEL: "Quille double",
    },
    submit: "Rechercher",
    formInstructions:
      "Indiquez le tirant d'eau maximal admissible, en mètres, et/ou choisissez une configuration de quille. HullQ n'affiche que les bateaux dont le courtier a confirmé qu'ils respectent ces exigences.",
    invalidTitle: "Ce lien de recherche n'est pas valide",
    invalidFallback:
      "Indiquez le tirant d'eau maximal sous forme de nombre décimal simple en mètres (par exemple 1.6) et/ou choisissez une configuration de quille prise en charge.",
    startOver: "Commencer une nouvelle recherche",
    serviceUnavailableTitle: "La recherche est temporairement indisponible",
    serviceUnavailableMessage:
      "Nous n'avons pas pu effectuer cette recherche pour le moment. Veuillez réessayer dans un instant.",
    requirementSummary: (draftMax) => `Bateaux dont le tirant d'eau confirmé est de ${draftMax} m ou moins.`,
    requirementSummaryKeelOnly: (keelLabel) =>
      `Bateaux avec configuration de quille confirmée : ${keelLabel}.`,
    requirementSummaryMixed: (draftMax, keelLabel) =>
      `Bateaux dont le tirant d'eau confirmé est de ${draftMax} m ou moins, avec configuration de quille : ${keelLabel}.`,
    confirmedHeading: "Résultats confirmés",
    noConfirmedMatches:
      "Aucune annonce ne dispose actuellement d'une confirmation du courtier attestant que son tirant d'eau respecte cette exigence.",
    noConfirmedMatchesGeneric:
      "Aucune annonce ne dispose actuellement d'une confirmation du courtier attestant qu'elle respecte cette exigence.",
    resolvedDraftText: (resolvedDraftM) =>
      `tirant d'eau déclaré par le courtier : ${resolvedDraftM} m (non vérifié de manière indépendante)`,
    resolvedKeelText: (keelLabel) =>
      `configuration de quille déclarée par le courtier : ${keelLabel} (non vérifiée de manière indépendante)`,
    insufficientDataText: (count) =>
      `${count} annonce(s) supplémentaire(s) pourraient satisfaire cette exigence mais ne sont pas affichées comme correspondance : le tirant d'eau est manquant, inconnu, ou contredit la déclaration actuelle d'une autre organisation.`,
    insufficientDataTextGeneric: (count) =>
      `${count} annonce(s) supplémentaire(s) pourraient satisfaire cette exigence mais ne sont pas affichées comme correspondance : les informations du courtier sont manquantes, inconnues, ou contredisent la déclaration actuelle d'une autre organisation.`,
    viewListing: "Voir l'annonce",
    freshnessConfirmedLabel: "Confirmé à jour",
    freshnessDueLabel: "Reconfirmation attendue",
    freshnessDueNote:
      "Le courtier n'a pas reconfirmé cette annonce récemment ; elle sera bientôt masquée si elle n'est pas reconfirmée.",
    sensitivityFormNote:
      "Découvrez combien de résultats confirmés changent si vous essayez une valeur différente pour une exigence. Cela ne modifie pas votre recherche actuelle.",
    sensitivityDraftSubmitLabel: "Voir l'effet d'un tirant d'eau maximal différent",
    sensitivityKeelSubmitLabel: "Voir l'effet d'une configuration de quille différente",
    sensitivityAlternativeDraftLabel: "Tirant d'eau maximal alternatif (mètres)",
    sensitivityAlternativeKeelLabel: "Configuration de quille alternative",
    sensitivityPageTitle: "Sensibilité de l'exigence",
    sensitivityCurrentHeading: "Exigence actuelle",
    sensitivityAlternativeHeading: "Exigence alternative",
    sensitivityCurrentConfirmedLabel: (count) => `Résultats actuellement confirmés : ${count}`,
    sensitivityAlternativeConfirmedLabel: (count) =>
      `Résultats confirmés avec l'alternative : ${count}`,
    sensitivityNewlyConfirmedLabel: (count) => `${count} nouvellement confirmé(s) avec l'alternative`,
    sensitivityNoLongerConfirmedLabel: (count) =>
      `${count} n'est/ne sont plus confirmé(s) avec l'alternative`,
    sensitivityCurrentInsufficientLabel: (count) =>
      `${count} annonce(s) supplémentaire(s) ont des preuves insuffisantes selon l'exigence actuelle`,
    sensitivityAlternativeInsufficientLabel: (count) =>
      `${count} annonce(s) supplémentaire(s) ont des preuves insuffisantes selon l'exigence alternative`,
    sensitivityViewAlternativeSearch: "Voir cette recherche",
    sensitivityInvalidTitle: "Cette demande de sensibilité n'est pas valide",
    sensitivityInvalidFallback:
      "Choisissez une exigence actuellement active et indiquez une valeur de remplacement pour celle-ci.",
    sensitivityServiceUnavailableTitle: "La sensibilité est temporairement indisponible",
    sensitivityServiceUnavailableMessage:
      "Nous n'avons pas pu effectuer cette comparaison pour le moment. Veuillez réessayer dans un instant.",
    sensitivityMethodNotAllowedTitle: "Commencer par une recherche",
    sensitivityMethodNotAllowedMessage:
      "Cette page n'affiche un résultat qu'après l'envoi d'une modification d'exigence depuis la page de recherche.",
  },
  pt: {
    title: "Pesquisa: calado máximo",
    draftMaxLabel: "Calado máximo (metros)",
    draftMaxPlaceholder: "1.6",
    keelConfigurationLabel: "Configuração da quilha",
    keelConfigurationAnyOption: "Qualquer configuração de quilha",
    keelConfigurationLabels: {
      FIN: "Quilha simples",
      FIN_WITH_BULB: "Quilha com bolbo",
      WING: "Quilha com asas",
      CENTERBOARD: "Orça de deriva",
      LIFTING_KEEL: "Quilha retrátil",
      TWIN_KEEL: "Quilha dupla",
    },
    submit: "Pesquisar",
    formInstructions:
      "Indique o calado máximo admissível, em metros, e/ou escolha uma configuração de quilha. A HullQ apenas apresenta barcos cujo corretor confirmou cumprirem estes requisitos.",
    invalidTitle: "Esta ligação de pesquisa não é válida",
    invalidFallback:
      "Indique o calado máximo como um número decimal simples em metros (por exemplo 1.6) e/ou escolha uma configuração de quilha suportada.",
    startOver: "Iniciar nova pesquisa",
    serviceUnavailableTitle: "A pesquisa está temporariamente indisponível",
    serviceUnavailableMessage:
      "Não foi possível concluir esta pesquisa neste momento. Tente novamente dentro de instantes.",
    requirementSummary: (draftMax) => `A mostrar barcos com calado confirmado de ${draftMax} m ou menos.`,
    requirementSummaryKeelOnly: (keelLabel) =>
      `A mostrar barcos com configuração de quilha confirmada: ${keelLabel}.`,
    requirementSummaryMixed: (draftMax, keelLabel) =>
      `A mostrar barcos com calado confirmado de ${draftMax} m ou menos e configuração de quilha: ${keelLabel}.`,
    confirmedHeading: "Correspondências confirmadas",
    noConfirmedMatches:
      "Nenhum anúncio tem atualmente confirmação do corretor de que o calado cumpre este requisito.",
    noConfirmedMatchesGeneric:
      "Nenhum anúncio tem atualmente confirmação do corretor de que cumpre este requisito.",
    resolvedDraftText: (resolvedDraftM) =>
      `calado declarado pelo corretor: ${resolvedDraftM} m (não verificado de forma independente)`,
    resolvedKeelText: (keelLabel) =>
      `configuração de quilha declarada pelo corretor: ${keelLabel} (não verificada de forma independente)`,
    insufficientDataText: (count) =>
      `${count} anúncio(s) adicional(is) poderiam satisfazer este requisito mas não são apresentados como correspondência: o calado está em falta, é desconhecido, ou entra em conflito com a declaração atual de outra organização.`,
    insufficientDataTextGeneric: (count) =>
      `${count} anúncio(s) adicional(is) poderiam satisfazer este requisito mas não são apresentados como correspondência: a informação do corretor está em falta, é desconhecida, ou entra em conflito com a declaração atual de outra organização.`,
    viewListing: "Ver anúncio",
    freshnessConfirmedLabel: "Confirmado atual",
    freshnessDueLabel: "Reconfirmação pendente",
    freshnessDueNote:
      "O corretor não reconfirmou este anúncio recentemente; será ocultado em breve caso não seja reconfirmado.",
    sensitivityFormNote:
      "Veja quantas correspondências confirmadas mudam se experimentar um valor diferente para um requisito. Isto não altera a sua pesquisa atual.",
    sensitivityDraftSubmitLabel: "Ver o efeito de um calado máximo diferente",
    sensitivityKeelSubmitLabel: "Ver o efeito de uma configuração de quilha diferente",
    sensitivityAlternativeDraftLabel: "Calado máximo alternativo (metros)",
    sensitivityAlternativeKeelLabel: "Configuração de quilha alternativa",
    sensitivityPageTitle: "Sensibilidade do requisito",
    sensitivityCurrentHeading: "Requisito atual",
    sensitivityAlternativeHeading: "Requisito alternativo",
    sensitivityCurrentConfirmedLabel: (count) => `Correspondências atualmente confirmadas: ${count}`,
    sensitivityAlternativeConfirmedLabel: (count) =>
      `Correspondências confirmadas com a alternativa: ${count}`,
    sensitivityNewlyConfirmedLabel: (count) => `${count} recém-confirmada(s) com a alternativa`,
    sensitivityNoLongerConfirmedLabel: (count) =>
      `${count} deixou/deixaram de estar confirmada(s) com a alternativa`,
    sensitivityCurrentInsufficientLabel: (count) =>
      `${count} anúncio(s) adicional(is) têm evidência insuficiente ao abrigo do requisito atual`,
    sensitivityAlternativeInsufficientLabel: (count) =>
      `${count} anúncio(s) adicional(is) têm evidência insuficiente ao abrigo do requisito alternativo`,
    sensitivityViewAlternativeSearch: "Ver esta pesquisa",
    sensitivityInvalidTitle: "Este pedido de sensibilidade não é válido",
    sensitivityInvalidFallback:
      "Escolha um requisito atualmente ativo e indique um valor de substituição para o mesmo.",
    sensitivityServiceUnavailableTitle: "A sensibilidade está temporariamente indisponível",
    sensitivityServiceUnavailableMessage:
      "Não foi possível concluir esta comparação neste momento. Tente novamente dentro de instantes.",
    sensitivityMethodNotAllowedTitle: "Comece a partir de uma pesquisa",
    sensitivityMethodNotAllowedMessage:
      "Esta página só mostra um resultado depois de submeter uma alteração de requisito a partir da página de pesquisa.",
  },
  es: {
    title: "Búsqueda: calado máximo",
    draftMaxLabel: "Calado máximo (metros)",
    draftMaxPlaceholder: "1.6",
    keelConfigurationLabel: "Configuración de quilla",
    keelConfigurationAnyOption: "Cualquier configuración de quilla",
    keelConfigurationLabels: {
      FIN: "Quilla de aleta",
      FIN_WITH_BULB: "Quilla de aleta con bulbo",
      WING: "Quilla de alas",
      CENTERBOARD: "Orza abatible",
      LIFTING_KEEL: "Quilla retráctil",
      TWIN_KEEL: "Quilla doble",
    },
    submit: "Buscar",
    formInstructions:
      "Indique el calado máximo admisible, en metros, y/o elija una configuración de quilla. HullQ solo muestra barcos cuyo bróker ha confirmado que cumplen estos requisitos.",
    invalidTitle: "Este enlace de búsqueda no es válido",
    invalidFallback:
      "Indique el calado máximo como un número decimal simple en metros (por ejemplo 1.6) y/o elija una configuración de quilla admitida.",
    startOver: "Iniciar una nueva búsqueda",
    serviceUnavailableTitle: "La búsqueda no está disponible temporalmente",
    serviceUnavailableMessage:
      "No hemos podido completar esta búsqueda en este momento. Inténtelo de nuevo en unos instantes.",
    requirementSummary: (draftMax) => `Mostrando barcos con calado confirmado de ${draftMax} m o menos.`,
    requirementSummaryKeelOnly: (keelLabel) =>
      `Mostrando barcos con configuración de quilla confirmada: ${keelLabel}.`,
    requirementSummaryMixed: (draftMax, keelLabel) =>
      `Mostrando barcos con calado confirmado de ${draftMax} m o menos y configuración de quilla: ${keelLabel}.`,
    confirmedHeading: "Coincidencias confirmadas",
    noConfirmedMatches:
      "Ningún anuncio cuenta actualmente con confirmación del bróker de que su calado cumple este requisito.",
    noConfirmedMatchesGeneric:
      "Ningún anuncio cuenta actualmente con confirmación del bróker de que cumple este requisito.",
    resolvedDraftText: (resolvedDraftM) =>
      `calado declarado por el bróker: ${resolvedDraftM} m (no verificado de forma independiente)`,
    resolvedKeelText: (keelLabel) =>
      `configuración de quilla declarada por el bróker: ${keelLabel} (no verificada de forma independiente)`,
    insufficientDataText: (count) =>
      `${count} anuncio(s) adicional(es) podrían cumplir este requisito pero no se muestran como coincidencia: falta el calado, es desconocido, o entra en conflicto con la declaración actual de otra organización.`,
    insufficientDataTextGeneric: (count) =>
      `${count} anuncio(s) adicional(es) podrían cumplir este requisito pero no se muestran como coincidencia: falta información del bróker, es desconocida, o entra en conflicto con la declaración actual de otra organización.`,
    viewListing: "Ver anuncio",
    freshnessConfirmedLabel: "Confirmado vigente",
    freshnessDueLabel: "Reconfirmación pendiente",
    freshnessDueNote:
      "El bróker no ha reconfirmado este anuncio recientemente; se ocultará pronto si no se reconfirma.",
    sensitivityFormNote:
      "Vea cuántas coincidencias confirmadas cambian si prueba un valor diferente para un requisito. Esto no modifica su búsqueda actual.",
    sensitivityDraftSubmitLabel: "Ver el efecto de un calado máximo diferente",
    sensitivityKeelSubmitLabel: "Ver el efecto de una configuración de quilla diferente",
    sensitivityAlternativeDraftLabel: "Calado máximo alternativo (metros)",
    sensitivityAlternativeKeelLabel: "Configuración de quilla alternativa",
    sensitivityPageTitle: "Sensibilidad del requisito",
    sensitivityCurrentHeading: "Requisito actual",
    sensitivityAlternativeHeading: "Requisito alternativo",
    sensitivityCurrentConfirmedLabel: (count) => `Coincidencias actualmente confirmadas: ${count}`,
    sensitivityAlternativeConfirmedLabel: (count) =>
      `Coincidencias confirmadas con la alternativa: ${count}`,
    sensitivityNewlyConfirmedLabel: (count) => `${count} recién confirmada(s) con la alternativa`,
    sensitivityNoLongerConfirmedLabel: (count) => `${count} ya no confirmada(s) con la alternativa`,
    sensitivityCurrentInsufficientLabel: (count) =>
      `${count} anuncio(s) adicional(es) tienen evidencia insuficiente según el requisito actual`,
    sensitivityAlternativeInsufficientLabel: (count) =>
      `${count} anuncio(s) adicional(es) tienen evidencia insuficiente según el requisito alternativo`,
    sensitivityViewAlternativeSearch: "Ver esta búsqueda",
    sensitivityInvalidTitle: "Esta solicitud de sensibilidad no es válida",
    sensitivityInvalidFallback:
      "Elija un requisito actualmente activo e indique un valor de sustitución para él.",
    sensitivityServiceUnavailableTitle: "La sensibilidad no está disponible temporalmente",
    sensitivityServiceUnavailableMessage:
      "No hemos podido completar esta comparación en este momento. Inténtelo de nuevo en unos instantes.",
    sensitivityMethodNotAllowedTitle: "Comience desde una búsqueda",
    sensitivityMethodNotAllowedMessage:
      "Esta página solo muestra un resultado después de enviar un cambio de requisito desde la página de búsqueda.",
  },
};
