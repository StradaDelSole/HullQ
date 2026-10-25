// SLICE-0089: localized presentation text for the download/print control
// and periodic-subscription settings added to the broker performance page.
// Mirrors `searchText.ts`'s per-locale dictionary pattern. Only these NEW
// controls are localized -- the pre-existing SLICE-0075 factual snapshot
// prose on this page is out of this slice's bounded scope (see completion
// report scope note).

export type SupportedLocale = "en" | "de" | "fr" | "pt" | "es";

export const SUPPORTED_LOCALES: readonly SupportedLocale[] = ["en", "de", "fr", "pt", "es"];

export interface ReportControlsText {
  reportHeading: string;
  downloadLabel: string;
  printLabel: string;
  localeLabel: string;
  subscriptionHeading: string;
  statusLabel: string;
  statusActive: string;
  statusInactive: string;
  periodKindLabel: string;
  periodWeekly: string;
  periodMonthly: string;
  recipientLabel: string;
  recipientPlaceholder: string;
  saveLabel: string;
  savedNotice: string;
  errorRoleRequired: string;
  errorInvalidInput: string;
  errorVersionConflict: string;
  errorGeneric: string;
  activeRequiresRecipientHint: string;
}

export const reportControlsText: Record<SupportedLocale, ReportControlsText> = {
  en: {
    reportHeading: "Report",
    downloadLabel: "Download report",
    printLabel: "Print / view report",
    localeLabel: "Report language",
    subscriptionHeading: "Periodic delivery",
    statusLabel: "Status",
    statusActive: "Active",
    statusInactive: "Inactive",
    periodKindLabel: "Frequency",
    periodWeekly: "Weekly",
    periodMonthly: "Monthly",
    recipientLabel: "Recipient email",
    recipientPlaceholder: "name@example.com",
    saveLabel: "Save",
    savedNotice: "Saved.",
    errorRoleRequired: "Only an Organization Owner or Admin can change this.",
    errorInvalidInput: "Please check the entered values.",
    errorVersionConflict: "This setting changed elsewhere -- reloaded with the latest values.",
    errorGeneric: "Something went wrong saving this setting. Please try again.",
    activeRequiresRecipientHint: "A recipient email is required to activate periodic delivery.",
  },
  de: {
    reportHeading: "Bericht",
    downloadLabel: "Bericht herunterladen",
    printLabel: "Bericht drucken / ansehen",
    localeLabel: "Berichtssprache",
    subscriptionHeading: "Regelmäßiger Versand",
    statusLabel: "Status",
    statusActive: "Aktiv",
    statusInactive: "Inaktiv",
    periodKindLabel: "Häufigkeit",
    periodWeekly: "Wöchentlich",
    periodMonthly: "Monatlich",
    recipientLabel: "Empfänger-E-Mail",
    recipientPlaceholder: "name@beispiel.de",
    saveLabel: "Speichern",
    savedNotice: "Gespeichert.",
    errorRoleRequired: "Nur ein Organisations-Owner oder -Admin kann dies ändern.",
    errorInvalidInput: "Bitte überprüfen Sie die eingegebenen Werte.",
    errorVersionConflict:
      "Diese Einstellung wurde anderswo geändert -- mit den aktuellen Werten neu geladen.",
    errorGeneric: "Beim Speichern ist ein Fehler aufgetreten. Bitte erneut versuchen.",
    activeRequiresRecipientHint:
      "Für die Aktivierung des regelmäßigen Versands ist eine Empfänger-E-Mail erforderlich.",
  },
  fr: {
    reportHeading: "Rapport",
    downloadLabel: "Télécharger le rapport",
    printLabel: "Imprimer / afficher le rapport",
    localeLabel: "Langue du rapport",
    subscriptionHeading: "Envoi périodique",
    statusLabel: "Statut",
    statusActive: "Actif",
    statusInactive: "Inactif",
    periodKindLabel: "Fréquence",
    periodWeekly: "Hebdomadaire",
    periodMonthly: "Mensuel",
    recipientLabel: "E-mail du destinataire",
    recipientPlaceholder: "nom@exemple.fr",
    saveLabel: "Enregistrer",
    savedNotice: "Enregistré.",
    errorRoleRequired:
      "Seul un propriétaire ou administrateur de l'organisation peut modifier ceci.",
    errorInvalidInput: "Veuillez vérifier les valeurs saisies.",
    errorVersionConflict:
      "Ce paramètre a été modifié ailleurs -- rechargé avec les dernières valeurs.",
    errorGeneric: "Une erreur s'est produite lors de l'enregistrement. Veuillez réessayer.",
    activeRequiresRecipientHint:
      "Un e-mail de destinataire est requis pour activer l'envoi périodique.",
  },
  pt: {
    reportHeading: "Relatório",
    downloadLabel: "Baixar relatório",
    printLabel: "Imprimir / visualizar relatório",
    localeLabel: "Idioma do relatório",
    subscriptionHeading: "Envio periódico",
    statusLabel: "Status",
    statusActive: "Ativo",
    statusInactive: "Inativo",
    periodKindLabel: "Frequência",
    periodWeekly: "Semanal",
    periodMonthly: "Mensal",
    recipientLabel: "E-mail do destinatário",
    recipientPlaceholder: "nome@exemplo.pt",
    saveLabel: "Salvar",
    savedNotice: "Salvo.",
    errorRoleRequired: "Somente um Owner ou Admin da organização pode alterar isso.",
    errorInvalidInput: "Verifique os valores informados.",
    errorVersionConflict:
      "Esta configuração foi alterada em outro lugar -- recarregada com os valores mais recentes.",
    errorGeneric: "Algo deu errado ao salvar esta configuração. Tente novamente.",
    activeRequiresRecipientHint:
      "Um e-mail de destinatário é obrigatório para ativar o envio periódico.",
  },
  es: {
    reportHeading: "Informe",
    downloadLabel: "Descargar informe",
    printLabel: "Imprimir / ver informe",
    localeLabel: "Idioma del informe",
    subscriptionHeading: "Envío periódico",
    statusLabel: "Estado",
    statusActive: "Activo",
    statusInactive: "Inactivo",
    periodKindLabel: "Frecuencia",
    periodWeekly: "Semanal",
    periodMonthly: "Mensual",
    recipientLabel: "Correo del destinatario",
    recipientPlaceholder: "nombre@ejemplo.es",
    saveLabel: "Guardar",
    savedNotice: "Guardado.",
    errorRoleRequired: "Solo un Owner o Admin de la organización puede cambiar esto.",
    errorInvalidInput: "Por favor revise los valores ingresados.",
    errorVersionConflict:
      "Esta configuración cambió en otro lugar -- se recargó con los valores más recientes.",
    errorGeneric: "Algo salió mal al guardar esta configuración. Intente nuevamente.",
    activeRequiresRecipientHint:
      "Se requiere un correo de destinatario para activar el envío periódico.",
  },
};
