/**
 * Template chrome: navigation labels and structural UI text.
 *
 * This file is the *only* place in the template where a human-readable string is authored, and it
 * deliberately contains nothing about a client. Every statement about the business — name, address,
 * services, hours, prices, disclaimers, legal texts, form labels — comes from the content artifact
 * (`docs/ARCHITECTURE.md` §1: "AI generates DATA, not CODE"; no React component contains client
 * copy). Anything that would have to change per client belongs in the content model instead.
 */
export const UI = {
  skipToContent: "Zum Inhalt springen",
  primaryNav: "Hauptnavigation",
  legalNav: "Rechtliche Hinweise",
  footerContactHeading: "Kontakt",
  footerHoursHeading: "Sprechzeiten",
  footerLegalHeading: "Rechtliches",
  footerDisclaimerHeading: "Medizinischer Hinweis",
  footerUpdatedPrefix: "Stand der Rechtstexte: ",
  imprintLinkLabel: "Impressum",
  privacyLinkLabel: "Datenschutzerklärung",
  detailsAbout: (title: string) => `Details zu ${title}`,
  emergencyHeading: "Im Notfall",
  channelsHeadingFallback: "Kontaktmöglichkeiten",
  arrivalHeading: "Anfahrt und Barrierefreiheit",
  accessibilityHeading: "Barrierefreiheit",
  accessLabels: {
    stepFree: "Stufenloser Zugang",
    elevator: "Aufzug vorhanden",
    accessibleToilet: "Barrierefreie Toilette",
  },
  accessYes: "ja",
  accessNo: "nein",
  parkingHeading: "Parken",
  transportHeading: "Öffentliche Verkehrsmittel",
  labelPhone: "Telefon: ",
  labelEmail: "E-Mail: ",
  labelLanguages: "Sprachen: ",
  labelFocusAreas: "Schwerpunkte: ",
  /**
   * Legal page structure labels. The legal *content* (Impressum, Datenschutz) comes from the
   * content artifact; the section headings below are the statutory structure (DDG § 5, MStV § 18,
   * DSGVO Art. 13/14) that every German site must present in the same shape.
   */
  imprintHeading: "Impressum",
  imprintProviderHeading: "Angaben gemäß § 5 DDG",
  imprintRepresentedBy: "Vertreten durch",
  imprintContactHeading: "Kontakt",
  imprintProfessionalHeading: "Berufsbezeichnung und zuständige Kammer",
  imprintRegulationsHeading: "Berufsrechtliche Regelungen",
  imprintVatHeading: "Umsatzsteuer-Identifikationsnummer",
  imprintResponsibleHeading: "Verantwortlich für den Inhalt (§ 18 Abs. 2 MStV)",
  imprintDisputeHeading: "Verbraucherstreitbeilegung",
  imprintLiabilityHeading: "Haftung für Inhalte und Links",
  imprintCopyrightHeading: "Urheberrecht",
  privacyHeading: "Datenschutzerklärung",
  privacyControllerHeading: "Verantwortlicher",
  privacyDpoHeading: "Datenschutzbeauftragte Person",
  privacyHostingHeading: "Hosting",
  privacyLegalBasisHeading: "Rechtsgrundlagen",
  privacyDataCategoriesHeading: "Verarbeitete Daten",
  privacyRecipientsHeading: "Empfänger",
  privacyRetentionHeading: "Speicherdauer",
  privacyRightsHeading: "Ihre Rechte",
  privacyCookiesHeading: "Cookies und Einwilligung",
  privacyFormHeading: "Kontaktformular",
  privacyNoTrackingHeading: "Keine Drittanbieter, kein Tracking",
  privacyAuthorityHeading: "Zuständige Aufsichtsbehörde",
  legalLastUpdatedPrefix: "Stand: ",
  labelSupervisingAuthority: "Aufsichtsbehörde: ",
  labelChamber: "Kammer: ",
  notFoundHeading: "404 – Seite nicht gefunden",
  notFoundBody:
    "Die aufgerufene Seite existiert nicht. Über die Navigation oder den folgenden Link gelangen Sie zurück zum Start.",
  backToHome: "Zur Startseite",
} as const;
