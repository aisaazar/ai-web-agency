#!/usr/bin/env node
/**
 * Generate a private sales-demo artifact from public prospect facts.
 * The output intentionally remains a fixture and can never satisfy pilot production gates.
 */
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const fixturePath = path.join(root, "sites", "_template-base", "content.dental-clinic.json");
const outputDir = path.join(root, ".artifacts", "sales-demo-wittmann");
const outputPath = path.join(outputDir, "content.demo.json");
const data = JSON.parse((await readFile(fixturePath, "utf8")).replace(/^\uFEFF/u, ""));

Object.assign(data.meta, {
  client_slug: "demo-dr-stefan-wittmann",
  is_fixture: true,
  note: "Private sales redesign concept based only on public prospect information. Not an authorized client site and never for production."
});
Object.assign(data.site, {
  name: "Mundgesundheit Schwabach",
  short_name: "Mundgesundheit Schwabach",
  tagline: "Moderne Behandlung. Fundierte Beratung. Angstfreie Patienten.",
  url: "https://demo.local",
  description: "Private redesign concept for a dental practice in Schwabach, based on publicly listed practice information.",
  theme_color: "#1E3A8A"
});
Object.assign(data.business, {
  legal_name: "Dr. Stefan Wittmann",
  brand_name: "Mundgesundheit Schwabach",
  address: {
    street: "Südliche Ringstraße 32",
    postal_code: "91126",
    city: "Schwabach",
    region: "Bayern",
    country: "DE"
  },
  contact: {
    phone: "+49 (0)9122 / 2171",
    email: "Stefan.Wittmann@dzn.de",
    emergency_phone: "+49 (0)9122 / 2171",
    emergency_note: "For urgent situations, contact the practice by telephone."
  },
  opening_hours: [
    { days: ["Mo", "Tu", "We", "Th"], slots: [{ opens: "08:00", closes: "12:00" }, { opens: "14:00", closes: "18:00" }] },
    { days: ["Fr"], slots: [{ opens: "08:00", closes: "12:00" }] }
  ],
  spoken_languages: ["de"],
  accessibility: {
    step_free_entrance: false,
    elevator: false,
    accessible_toilet: false,
    notes: "Accessibility details are not asserted in this private demo; verify directly with the practice before publication."
  },
  parking: "Parking and access details should be verified directly before publication.",
  public_transport: "Public-transport directions should be verified directly before publication.",
  map: {
    link_url: "https://www.google.com/maps/search/?api=1&query=S%C3%BCdliche+Ringstra%C3%9Fe+32%2C+91126+Schwabach",
    link_label: "Route in Google Maps öffnen",
    note: "External map opens only after an intentional click."
  }
});

Object.assign(data.compliance, {
  medical_disclaimer: [
    "Diese private Konzeptseite dient ausschließlich der Demonstration von Webdesign und ersetzt keine individuelle medizinische Beratung.",
    "Alle produktiven Rechtstexte und Praxisangaben müssen vor Veröffentlichung geprüft und freigegeben werden."
  ],
  legal_review_status: "pending",
  notes: "Private sales demo; not an authorized client website."
});
Object.assign(data.hero, {
  eyebrow: "PRIVATE REDESIGN DEMO",
  headline: "Zahnarztpraxis in Schwabach – klar, modern und persönlich.",
  subheadline: "Moderne Behandlung, fundierte Beratung und ein ruhiger digitaler Auftritt.",
  paragraphs: [
    "Die Praxis von Dr. Stefan Wittmann in Schwabach bietet ein breites Spektrum zahnmedizinischer Leistungen.",
    "Diese private Konzeptseite zeigt, wie die vorhandenen Informationen klarer und mobilfreundlich strukturiert werden können."
  ],
  primary_cta: { label: "Termin anfragen", href: "#kontakt" },
  secondary_cta: { label: "Leistungen ansehen", href: "/leistungen" }
});

data.highlights = [
  { icon: "shield", title: "Fundierte Beratung", body: "Informationen werden klar strukturiert und auf die wichtigsten Fragen der Patientinnen und Patienten fokussiert." },
  { icon: "sparkle", title: "Moderne Behandlung", body: "Der öffentliche Praxisauftritt nennt unter anderem Keramikimplantate, Alignerschienen und Schlafapnoeschienen." },
  { icon: "heart", title: "Persönlicher Kontakt", body: "Telefonische und digitale Kontaktmöglichkeiten werden auf mobilen Geräten deutlich sichtbar platziert." }
];

data.services = {
  heading: "Leistungen",
  intro: [
    "Aus dem öffentlichen Praxisauftritt wurden folgende Themen für die private Design-Demo übernommen.",
    "Die Demo formuliert keine zusätzlichen medizinischen Versprechen."
  ],
  note: "Private Demo. Medizinische Inhalte und rechtliche Texte müssen vor Veröffentlichung durch die Praxis geprüft werden.",
  items: [
    {
      id: "keramikimplantate",
      title: "Keramikimplantate",
      summary: "Die Praxis nennt Keramikimplantate als einen ihrer Behandlungsschwerpunkte.",
      paragraphs: ["Die konkrete Eignung und Behandlung wird individuell in der Praxis beurteilt."],
      features: ["Öffentlich genannt auf der Praxis-Website", "Individuelle Beratung", "Praxisgespräch"],
      icon: "tooth"
    },
    {
      id: "aligner",
      title: "Alignerschienen",
      summary: "Unsichtbare Schienen werden auf der aktuellen Praxis-Website als kosmetische Korrektur der Zahnstellung beschrieben.",
      paragraphs: ["Details zu Diagnose, Ablauf und Indikation sollten direkt mit der Praxis abgestimmt werden."],
      features: ["Öffentlich genannte Leistung", "Beratung", "Individuelle Planung"],
      icon: "sparkle"
    },
    {
      id: "schlafapnoe",
      title: "Schlafapnoe- und Schnarchschienen",
      summary: "Die Praxis führt Schlafapnoeschienen in ihrem öffentlichen Leistungsangebot.",
      paragraphs: ["Die Demo stellt die Leistung informativ dar und ersetzt keine medizinische Beratung."],
      features: ["Öffentlich genannter Schwerpunkt", "Beratung", "Individuelle Prüfung"],
      icon: "shield"
    }
  ]
};
data.team = {
  heading: "Praxis",
  intro: ["Private demo uses only the publicly identified practice owner name; staff details are intentionally omitted until authorized client data is supplied."],
  members: [
    {
      id: "stefan-wittmann",
      name: "Dr. Stefan Wittmann",
      role: "Zahnarzt",
      qualifications: ["Zahnarzt"],
      focus_areas: ["Zahnersatz", "Keramikimplantate", "Alignerschienen", "Prophylaxe"],
      languages: ["de"],
      bio: ["Praxisinhaber laut öffentlichem Praxisauftritt."],
      photo_url: null
    }
  ]
};

data.hours = {
  heading: "Besuch & Erreichbarkeit",
  intro: ["Die Praxis ist Montag bis Freitag zu den öffentlich angegebenen Zeiten erreichbar."],
  appointment_note: "Termine werden telefonisch vereinbart; das aktuelle öffentliche Angebot beschreibt zusätzlich einen Kontakt über das Formular.",
  note: "Öffnungszeiten und Kontaktdaten vor Veröffentlichung erneut mit der Praxis verifizieren."
};

data.contact = {
  heading: "Termin & Kontakt",
  intro: [
    "Diese private Konzeptseite zeigt eine klarere Kontaktführung für mobile Besucherinnen und Besucher.",
    "Für den echten Betrieb müssen Datenschutzhinweise, Consent und der produktive Lead-Endpunkt freigegeben werden."
  ],
  channels_heading: "Direktkontakt",
  reply_note: "Kontaktkanäle basieren auf öffentlich angegebenen Praxisdaten.",
  form: {
    heading: "Termin anfragen",
    intro: ["Name, E-Mail und Nachricht reichen für eine erste Anfrage."],
    consent_label: "Ich stimme der Verarbeitung meiner Angaben zur Bearbeitung meiner Anfrage zu.",
    submit_label: "Anfrage senden",
    submitting_label: "Wird gesendet …",
    success_message: "Private Demo: Anfrage erfolgreich vorbereitet.",
    failure_message: "Die Demo kann derzeit keine produktive Anfrage übermitteln.",
    offline_notice: "PRIVATE DEMO — kein produktiver Lead-Endpunkt angeschlossen.",
    labels: {
      name: "Name",
      email: "E-Mail",
      phone: "Telefon",
      phone_optional: "optional",
      message: "Nachricht",
      required_hint: "Pflichtfeld",
      optional_hint: "optional",
      error_required: "Bitte füllen Sie dieses Feld aus.",
      error_email: "Bitte geben Sie eine gültige E-Mail-Adresse ein.",
      error_summary: "Bitte prüfen Sie die markierten Felder."
    }
  }
};
data.faq = {
  heading: "Häufige Fragen",
  intro: "Die Demo beantwortet nur Fragen, die aus den öffentlich sichtbaren Praxisinformationen ableitbar sind.",
  items: [
    { question: "Wo befindet sich die Praxis?", answer: ["Südliche Ringstraße 32, 91126 Schwabach."] },
    { question: "Wann ist die Praxis geöffnet?", answer: ["Montag bis Donnerstag 08:00–12:00 und 14:00–18:00 Uhr; Freitag 08:00–12:00 Uhr, laut aktuellem öffentlichen Praxisauftritt."] },
    { question: "Wie kann ich einen Termin anfragen?", answer: ["Telefonisch unter +49 (0)9122 / 2171 oder über das aktuell auf der Website angebotene Kontaktformular."] }
  ]
};

data.legal = {
  imprint: {
    provider_name: "PRIVATE REDESIGN DEMO",
    legal_form: "Not for publication",
    represented_by: ["AI Web Agency demo"],
    address: {
      street: "Not for publication",
      postal_code: "00000",
      city: "Demo",
      region: "DE",
      country: "DE"
    },
    contact: { phone: "Not for publication", email: "demo@ai-web-agency.example" },
    professional_title: "Not applicable",
    professional_title_country: "Deutschland",
    professional_body: { name: "Not applicable", url: "https://www.blzk.de/", supervising_authority: "Not for publication" },
    professional_regulations: [{ name: "Demo placeholder — verify before publication", url: "https://www.blzk.de/" }],
    vat_id: "DEMO-NOT-FOR-PRODUCTION",
    responsible_for_content: {
      name: "AI Web Agency demo",
      address: {
        street: "Not for publication",
        postal_code: "00000",
        city: "Demo",
        region: "DE",
        country: "DE"
      }
    },
    dispute_resolution: ["Private design concept. No client relationship is represented."],
    liability_notes: ["This page is a private design demo and is not a production medical website."],
    copyright_notes: ["Do not publish or reuse third-party material without authorization."],
    last_updated: "2026-10-01"
  },
  privacy: {
    controller: {
      name: "PRIVATE REDESIGN DEMO",
      address: {
        street: "Not for publication",
        postal_code: "00000",
        city: "Demo",
        region: "DE",
        country: "DE"
      }
    },
    controller_contact: { phone: "Not for publication", email: "demo@ai-web-agency.example" },
    data_protection_officer: null,
    hosting: { provider: "Local/private demo", location: "Not for publication", note: "No production processing is represented." },
    legal_basis: [{ heading: "Demo only", paragraphs: ["No production data processing is intended by this private concept."] }],
    data_categories: [{ heading: "No client data", paragraphs: ["Do not submit personal or medical data to this demo."] }],
    recipients: ["None for this local demo."],
    retention: ["No production retention is represented."],
    rights: [{ heading: "Demo", paragraphs: ["Production privacy information must be supplied and reviewed before launch."] }],
    cookies_notice: "No non-essential tracking is represented in this demo.",
    contact_form_notice: "The form is a visual demo only.",
    no_tracking_notice: "No analytics or tracking is represented in this demo.",
    supervisory_authority: { name: "Bayerisches Landesamt für Datenschutzaufsicht", url: "https://www.lda.bayern.de/", address: { street: "Promenade 27", postal_code: "91522", city: "Ansbach", region: "Bayern", country: "DE" } },
    last_updated: "2026-10-01"
  }
};

data.seo = {
  pages: [
    { path: "/", title: "Mundgesundheit Schwabach | Private Redesign Demo", description: "Private, nicht autorisierte Website-Redesign-Demo für eine Zahnarztpraxis in Schwabach." },
    { path: "/leistungen", title: "Leistungen | Private Redesign Demo", description: "Private demo overview of publicly listed practice services." },
    { path: "/impressum", title: "Impressum | Private Redesign Demo", description: "Private redesign demo imprint placeholder — not for publication or production use." },
    { path: "/datenschutz", title: "Datenschutz | Private Redesign Demo", description: "Private redesign demo privacy placeholder — not for publication or production use." }
  ]
};

await mkdir(outputDir, { recursive: true });
await writeFile(outputPath, JSON.stringify(data, null, 2), "utf8");
console.log(outputPath);
