// SLICE-0058: localized presentation text for the anonymous local shortlist
// surfaces (`/{locale}/shortlist` plus the add/remove control shared with
// Search results and the public listing page). Technical identifiers
// (NativeListingId, storage keys, freshness status tokens) stay
// language-neutral; only this prose is translated.
//
// Contract §12 (copy/decision neutrality): shortlist membership is buyer
// interest, never a HullQ verdict -- none of this text may say
// "recommended", "best fit", "matched for you", "top choice" or "HullQ
// selected".

export type SupportedLocale = "en" | "de" | "fr" | "pt" | "es";

export const SUPPORTED_LOCALES: readonly SupportedLocale[] = ["en", "de", "fr", "pt", "es"];

export interface ShortlistText {
  pageTitle: string;
  pageHeading: string;
  noscriptMessage: string;
  loadingMessage: string;
  emptyMessage: string;
  unavailableMessage: string;
  saveLabel: string;
  savedLabel: string;
  removeLabel: string;
  viewListing: string;
  /** SLICE-0059: link from `/{locale}/shortlist` into the factual Compare surface. */
  compareLinkLabel: string;
  priceOnApplicationLabel: string;
  freshnessConfirmedLabel: string;
  freshnessDueLabel: string;
  /** Page-level: the resolver request itself failed (contract §13). */
  serviceErrorTitle: string;
  serviceErrorMessage: string;
  /** One saved entry's resolution failed while others still rendered (contract §13). */
  itemServiceErrorMessage: string;
}

export const shortlistText: Record<SupportedLocale, ShortlistText> = {
  en: {
    pageTitle: "Your shortlist",
    pageHeading: "Your shortlist",
    noscriptMessage: "Your shortlist needs JavaScript enabled in your browser.",
    loadingMessage: "Loading your shortlist…",
    emptyMessage: "Your shortlist is empty. Add a listing from Search or a listing page.",
    unavailableMessage: "This saved listing is not currently available.",
    saveLabel: "Save to shortlist",
    savedLabel: "Saved",
    removeLabel: "Remove",
    viewListing: "View listing",
    compareLinkLabel: "Compare shortlist",
    priceOnApplicationLabel: "Price on application",
    freshnessConfirmedLabel: "Confirmed current",
    freshnessDueLabel: "Reconfirmation due",
    serviceErrorTitle: "Your shortlist is temporarily unavailable",
    serviceErrorMessage:
      "We couldn't load current listing details right now. Your saved listings are unaffected; please try again in a moment.",
    itemServiceErrorMessage: "We couldn't check this saved listing right now. It remains saved.",
  },
  de: {
    pageTitle: "Ihre Merkliste",
    pageHeading: "Ihre Merkliste",
    noscriptMessage: "Für Ihre Merkliste muss JavaScript in Ihrem Browser aktiviert sein.",
    loadingMessage: "Merkliste wird geladen…",
    emptyMessage:
      "Ihre Merkliste ist leer. Fügen Sie ein Angebot über die Suche oder eine Angebotsseite hinzu.",
    unavailableMessage: "Dieses gespeicherte Angebot ist derzeit nicht verfügbar.",
    saveLabel: "Zur Merkliste hinzufügen",
    savedLabel: "Gespeichert",
    removeLabel: "Entfernen",
    viewListing: "Angebot ansehen",
    compareLinkLabel: "Merkliste vergleichen",
    priceOnApplicationLabel: "Preis auf Anfrage",
    freshnessConfirmedLabel: "Aktuell bestätigt",
    freshnessDueLabel: "Bestätigung ausstehend",
    serviceErrorTitle: "Ihre Merkliste ist vorübergehend nicht verfügbar",
    serviceErrorMessage:
      "Aktuelle Angebotsdetails konnten gerade nicht geladen werden. Ihre gespeicherten Angebote sind davon nicht betroffen; bitte versuchen Sie es in Kürze erneut.",
    itemServiceErrorMessage:
      "Dieses gespeicherte Angebot konnte gerade nicht geprüft werden. Es bleibt gespeichert.",
  },
  fr: {
    pageTitle: "Votre liste de favoris",
    pageHeading: "Votre liste de favoris",
    noscriptMessage: "Votre liste de favoris nécessite que JavaScript soit activé dans votre navigateur.",
    loadingMessage: "Chargement de votre liste de favoris…",
    emptyMessage:
      "Votre liste de favoris est vide. Ajoutez une annonce depuis la recherche ou une page d'annonce.",
    unavailableMessage: "Cette annonce enregistrée n'est pas disponible actuellement.",
    saveLabel: "Ajouter à la liste de favoris",
    savedLabel: "Enregistrée",
    removeLabel: "Retirer",
    viewListing: "Voir l'annonce",
    compareLinkLabel: "Comparer la liste de favoris",
    priceOnApplicationLabel: "Prix sur demande",
    freshnessConfirmedLabel: "Confirmé à jour",
    freshnessDueLabel: "Reconfirmation attendue",
    serviceErrorTitle: "Votre liste de favoris est temporairement indisponible",
    serviceErrorMessage:
      "Nous n'avons pas pu charger les détails actuels des annonces pour le moment. Vos annonces enregistrées ne sont pas affectées ; veuillez réessayer dans un instant.",
    itemServiceErrorMessage:
      "Nous n'avons pas pu vérifier cette annonce enregistrée pour le moment. Elle reste enregistrée.",
  },
  pt: {
    pageTitle: "A sua lista de interesses",
    pageHeading: "A sua lista de interesses",
    noscriptMessage: "A sua lista de interesses requer JavaScript ativado no seu navegador.",
    loadingMessage: "A carregar a sua lista de interesses…",
    emptyMessage:
      "A sua lista de interesses está vazia. Adicione um anúncio a partir da pesquisa ou de uma página de anúncio.",
    unavailableMessage: "Este anúncio guardado não está atualmente disponível.",
    saveLabel: "Adicionar à lista de interesses",
    savedLabel: "Guardado",
    removeLabel: "Remover",
    viewListing: "Ver anúncio",
    compareLinkLabel: "Comparar lista de interesses",
    priceOnApplicationLabel: "Preço sob consulta",
    freshnessConfirmedLabel: "Confirmado atual",
    freshnessDueLabel: "Reconfirmação pendente",
    serviceErrorTitle: "A sua lista de interesses está temporariamente indisponível",
    serviceErrorMessage:
      "Não foi possível carregar os detalhes atuais dos anúncios neste momento. Os seus anúncios guardados não são afetados; tente novamente dentro de instantes.",
    itemServiceErrorMessage:
      "Não foi possível verificar este anúncio guardado neste momento. Continua guardado.",
  },
  es: {
    pageTitle: "Su lista de interés",
    pageHeading: "Su lista de interés",
    noscriptMessage: "Su lista de interés requiere JavaScript activado en su navegador.",
    loadingMessage: "Cargando su lista de interés…",
    emptyMessage:
      "Su lista de interés está vacía. Añada un anuncio desde la búsqueda o una página de anuncio.",
    unavailableMessage: "Este anuncio guardado no está disponible actualmente.",
    saveLabel: "Añadir a la lista de interés",
    savedLabel: "Guardado",
    removeLabel: "Quitar",
    viewListing: "Ver anuncio",
    compareLinkLabel: "Comparar lista de interés",
    priceOnApplicationLabel: "Precio a consultar",
    freshnessConfirmedLabel: "Confirmado vigente",
    freshnessDueLabel: "Reconfirmación pendiente",
    serviceErrorTitle: "Su lista de interés no está disponible temporalmente",
    serviceErrorMessage:
      "No hemos podido cargar los detalles actuales de los anuncios en este momento. Sus anuncios guardados no se ven afectados; inténtelo de nuevo en unos instantes.",
    itemServiceErrorMessage:
      "No hemos podido comprobar este anuncio guardado en este momento. Sigue guardado.",
  },
};
