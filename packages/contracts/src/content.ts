/* eslint-disable */
/**
 * Generated file - DO NOT EDIT.
 *
 * Source of truth: apps/api/src/agency/domain/content_model.py
 * Chain: Pydantic -> JSON Schema -> TypeScript (docs/CONTRACTS-AND-CONVENTIONS.md, ADR-004).
 * Regenerate with: npm run contracts
 */

export type AccessibleToilet = boolean;
export type Elevator = boolean;
export type Notes = string | null;
export type StepFreeEntrance = boolean;
export type City = string;
export type Country = "DE";
export type PostalCode = string;
export type Region = string | null;
export type Street = string;
export type BrandName = string;
/**
 * Allowlisted category -> JSON-LD type mapping (deterministic, ADR-013).
 */
export type BusinessType = "dental_clinic";
export type Email = string;
export type EmergencyNote = string | null;
export type EmergencyPhone = string | null;
/**
 * Human readable phone number.
 */
export type Phone = string;
export type Latitude = number;
export type Longitude = number;
/**
 * @minItems 1
 */
export type Insurance = [
  "gesetzlich" | "privat" | "selbstzahler",
  ...("gesetzlich" | "privat" | "selbstzahler")[],
];
/**
 * Drives which legal pages are required (ADR-014).
 */
export type Jurisdiction = "DE";
export type LegalName = string;
export type LinkLabel = string;
/**
 * Map opened by user click. No third-party embed and no cookie before consent.
 */
export type LinkUrl = string;
export type Note = string | null;
/**
 * @minItems 1
 */
export type OpeningHours = [OpeningHours1, ...OpeningHours1[]];
/**
 * @minItems 1
 */
export type Days = [
  "Mo" | "Tu" | "We" | "Th" | "Fr" | "Sa" | "Su",
  ...("Mo" | "Tu" | "We" | "Th" | "Fr" | "Sa" | "Su")[],
];
export type Note1 = string | null;
/**
 * @minItems 1
 */
export type Slots = [OpeningSlot, ...OpeningSlot[]];
export type Closes = string;
export type Opens = string;
export type Parking = string | null;
/**
 * @minItems 1
 */
export type PaymentMethods = [string, ...string[]];
/**
 * schema.org priceRange, e.g. '$$'.
 */
export type PriceRange = string | null;
export type PublicTransport = string | null;
/**
 * @minItems 1
 */
export type SpokenLanguages = ["de" | "en", ...("de" | "en")[]];
/**
 * A German lawyer reviews Impressum/Datenschutz/disclaimer once (docs/SECURITY-AND-RISKS.md). Production mode of the gate blocks `pending`.
 */
export type LegalReviewStatus = "pending" | "reviewed";
/**
 * Rendered in the footer and in llms.txt. Required for health categories.
 *
 * @minItems 1
 */
export type MedicalDisclaimer = [string, ...string[]];
export type Notes1 = string | null;
export type OgImageAlt = string | null;
export type ChannelsHeading = string;
export type ConsentLabel = string;
export type FailureMessage = string;
export type Heading = string;
/**
 * @minItems 1
 */
export type Intro = [string, ...string[]];
export type Email1 = string;
export type ErrorEmail = string;
export type ErrorRequired = string;
export type ErrorSummary = string;
export type Message = string;
export type Name = string;
export type OptionalHint = string;
export type Phone1 = string;
export type PhoneOptional = string;
export type RequiredHint = string;
/**
 * Shown when no lead endpoint is configured at build time (v1 scaffold has no backend).
 */
export type OfflineNotice = string;
export type SubmitLabel = string;
export type SubmittingLabel = string;
export type SuccessMessage = string;
export type Heading1 = string;
/**
 * @minItems 1
 */
export type Intro1 = [string, ...string[]];
export type ReplyNote = string | null;
/**
 * Enforced, not decorative (ADR-005). Templates declare the versions they support.
 */
export type ContentSchemaVersion = string;
export type Heading2 = string;
export type Intro2 = string | null;
/**
 * @minItems 1
 */
export type Items = [FaqItem, ...FaqItem[]];
/**
 * @minItems 1
 */
export type Answer = [string, ...string[]];
export type Question = string;
export type Eyebrow = string | null;
export type Headline = string;
/**
 * @minItems 1
 */
export type Paragraphs = [string, ...string[]];
export type Href = string;
export type Label = string;
export type Subheadline = string;
/**
 * @minItems 1
 */
export type Highlights = [Highlight, ...Highlight[]];
export type Body = string;
export type Icon =
  | "tooth"
  | "sparkle"
  | "shield"
  | "clock"
  | "phone"
  | "map-pin"
  | "users"
  | "heart"
  | "child"
  | "calendar";
export type Title = string;
export type AppointmentNote = string | null;
export type Heading3 = string;
/**
 * @minItems 1
 */
export type Intro3 = [string, ...string[]];
export type Note2 = string | null;
/**
 * @minItems 1
 */
export type CopyrightNotes = [string, ...string[]];
/**
 * @minItems 1
 */
export type DisputeResolution = [string, ...string[]];
export type LastUpdated = string;
export type LegalForm = string;
/**
 * @minItems 1
 */
export type LiabilityNotes = [string, ...string[]];
export type Name1 = string;
export type SupervisingAuthority = string;
export type Url = string;
/**
 * @minItems 1
 */
export type ProfessionalRegulations = [RegulationRef, ...RegulationRef[]];
export type Name2 = string;
export type Url1 = string;
export type ProfessionalTitle = string;
export type ProfessionalTitleCountry = string;
export type ProviderName = string;
/**
 * @minItems 1
 */
export type RepresentedBy = [string, ...string[]];
export type Name3 = string;
export type VatId = string | null;
export type ContactFormNotice = string;
export type CookiesNotice = string;
/**
 * @minItems 1
 */
export type DataCategories = [LegalSection, ...LegalSection[]];
export type Heading4 = string;
/**
 * @minItems 1
 */
export type Paragraphs1 = [string, ...string[]];
export type DataProtectionOfficer = string | null;
export type Location = string;
export type Note3 = string;
export type Provider = string;
export type LastUpdated1 = string;
/**
 * @minItems 1
 */
export type LegalBasis = [LegalSection, ...LegalSection[]];
/**
 * States that no third-party tracker is embedded (no Google Fonts CDN, no analytics, no map iframe).
 */
export type NoTrackingNotice = string;
/**
 * @minItems 1
 */
export type Recipients = [string, ...string[]];
/**
 * @minItems 1
 */
export type Retention = [string, ...string[]];
/**
 * @minItems 1
 */
export type Rights = [LegalSection, ...LegalSection[]];
export type Name4 = string;
export type Url2 = string;
export type Locale = string;
export type Heading5 = string;
export type Alt = string;
export type Caption = string | null;
export type Id = string;
export type Src = string;
export type Title1 = string;
export type Images = MediaImage[];
/**
 * @minItems 1
 */
export type Intro4 = [string, ...string[]];
export type Caption1 = string | null;
export type Id1 = string;
export type Poster = string | null;
export type Src1 = string;
export type Title2 = string;
export type Videos = MediaVideo[];
/**
 * Client entity slug (docs/DOMAIN-MODEL.md `clients.slug`).
 */
export type ClientSlug = string;
/**
 * True for demo/fixture content. The build gate refuses to publish fixture content.
 */
export type IsFixture = boolean;
/**
 * Human note. Never rendered as HTML, never part of the page copy.
 */
export type Note4 = string | null;
/**
 * One entry per generated page; sitemap, canonical and meta derive from it.
 *
 * @minItems 1
 */
export type Pages = [PageSeo, ...PageSeo[]];
export type Description = string;
export type Noindex = boolean;
export type Path = "/" | "/leistungen" | "/impressum" | "/datenschutz";
export type Title3 = string;
export type Heading6 = string;
/**
 * @minItems 1
 */
export type Intro5 = [string, ...string[]];
/**
 * @minItems 1
 */
export type Items1 = [Service, ...Service[]];
export type Features = string[];
export type Icon1 =
  | "tooth"
  | "sparkle"
  | "shield"
  | "clock"
  | "phone"
  | "map-pin"
  | "users"
  | "heart"
  | "child"
  | "calendar";
/**
 * Anchor id and stable reference; never localised.
 */
export type Id2 = string;
/**
 * @minItems 1
 */
export type Paragraphs2 = [string, ...string[]];
export type Summary = string;
export type Title4 = string;
export type Note5 = string | null;
/**
 * Default meta description, also used as the llms.txt summary.
 */
export type Description1 = string;
export type Name5 = string;
/**
 * Same-origin path of a build-time generated OG image.
 */
export type OgImage = string | null;
export type ShortName = string | null;
export type Tagline = string;
export type ThemeColor = string;
/**
 * Canonical origin of the site, e.g. https://praxis.example
 */
export type Url3 = string;
export type Heading7 = string;
/**
 * @minItems 1
 */
export type Intro6 = [string, ...string[]];
/**
 * @minItems 1
 */
export type Members = [TeamMember, ...TeamMember[]];
/**
 * @minItems 1
 */
export type Bio = [string, ...string[]];
export type FocusAreas = string[];
export type Id3 = string;
/**
 * @minItems 1
 */
export type Languages = ["de" | "en", ...("de" | "en")[]];
export type Name6 = string;
/**
 * Same-origin path to a client-approved photo; null renders initials.
 */
export type PhotoUrl = string | null;
/**
 * @minItems 1
 */
export type Qualifications = [string, ...string[]];
export type Role = string;

/**
 * One immutable content artifact revision (docs/DOMAIN-MODEL.md, artifact type `content_model`).
 */
export interface ContentModel {
  business: Business;
  compliance: Compliance;
  contact: ContactSection;
  content_schema_version: ContentSchemaVersion;
  faq: FaqSection;
  hero: HeroSection;
  highlights: Highlights;
  hours: HoursSection;
  legal: Legal;
  locale: Locale;
  media?: MediaSection | null;
  meta: ContentMeta;
  seo: Seo;
  services: ServicesSection;
  site: SiteIdentity;
  team: TeamSection;
}
/**
 * Typed business truth. Every value must trace back to an approved `client_fact`.
 */
export interface Business {
  accessibility: Accessibility;
  address: Address;
  brand_name: BrandName;
  business_type: BusinessType;
  contact: ContactDetails;
  geo: GeoPoint;
  insurance: Insurance;
  jurisdiction: Jurisdiction;
  legal_name: LegalName;
  map: MapInfo;
  opening_hours: OpeningHours;
  parking?: Parking;
  payment_methods: PaymentMethods;
  price_range?: PriceRange;
  public_transport?: PublicTransport;
  spoken_languages: SpokenLanguages;
}
export interface Accessibility {
  accessible_toilet: AccessibleToilet;
  elevator: Elevator;
  notes?: Notes;
  step_free_entrance: StepFreeEntrance;
}
export interface Address {
  city: City;
  country?: Country;
  postal_code: PostalCode;
  region?: Region;
  street: Street;
}
export interface ContactDetails {
  email: Email;
  emergency_note?: EmergencyNote;
  emergency_phone?: EmergencyPhone;
  phone: Phone;
}
export interface GeoPoint {
  latitude: Latitude;
  longitude: Longitude;
}
export interface MapInfo {
  link_label: LinkLabel;
  link_url: LinkUrl;
  note?: Note;
}
export interface OpeningHours1 {
  days: Days;
  note?: Note1;
  slots: Slots;
}
export interface OpeningSlot {
  closes: Closes;
  opens: Opens;
}
export interface Compliance {
  legal_review_status: LegalReviewStatus;
  medical_disclaimer: MedicalDisclaimer;
  notes?: Notes1;
  og_image_alt?: OgImageAlt;
}
export interface ContactSection {
  channels_heading: ChannelsHeading;
  form: ContactForm;
  heading: Heading1;
  intro: Intro1;
  reply_note?: ReplyNote;
}
export interface ContactForm {
  consent_label: ConsentLabel;
  failure_message: FailureMessage;
  heading: Heading;
  intro: Intro;
  labels: ContactFormLabels;
  offline_notice: OfflineNotice;
  submit_label: SubmitLabel;
  submitting_label: SubmittingLabel;
  success_message: SuccessMessage;
}
export interface ContactFormLabels {
  email: Email1;
  error_email: ErrorEmail;
  error_required: ErrorRequired;
  error_summary: ErrorSummary;
  message: Message;
  name: Name;
  optional_hint: OptionalHint;
  phone: Phone1;
  phone_optional: PhoneOptional;
  required_hint: RequiredHint;
}
export interface FaqSection {
  heading: Heading2;
  intro?: Intro2;
  items: Items;
}
export interface FaqItem {
  answer: Answer;
  question: Question;
}
export interface HeroSection {
  eyebrow?: Eyebrow;
  headline: Headline;
  paragraphs: Paragraphs;
  primary_cta: Cta;
  secondary_cta?: Cta | null;
  subheadline: Subheadline;
}
export interface Cta {
  href: Href;
  label: Label;
}
export interface Highlight {
  body: Body;
  icon: Icon;
  title: Title;
}
export interface HoursSection {
  appointment_note?: AppointmentNote;
  heading: Heading3;
  intro: Intro3;
  note?: Note2;
}
export interface Legal {
  imprint: Imprint;
  privacy: Privacy;
}
/**
 * Impressum content (DE: section 5 DDG, formerly TMG; section 18 (2) MStV).
 */
export interface Imprint {
  address: Address;
  contact: ContactDetails;
  copyright_notes: CopyrightNotes;
  dispute_resolution: DisputeResolution;
  last_updated: LastUpdated;
  legal_form: LegalForm;
  liability_notes: LiabilityNotes;
  professional_body: ProfessionalBody;
  professional_regulations: ProfessionalRegulations;
  professional_title: ProfessionalTitle;
  professional_title_country: ProfessionalTitleCountry;
  provider_name: ProviderName;
  represented_by: RepresentedBy;
  responsible_for_content: ResponsiblePerson;
  vat_id?: VatId;
}
export interface ProfessionalBody {
  name: Name1;
  supervising_authority: SupervisingAuthority;
  url: Url;
}
export interface RegulationRef {
  name: Name2;
  url: Url1;
}
export interface ResponsiblePerson {
  address: Address;
  name: Name3;
}
/**
 * Datenschutzerklaerung content (DSGVO Art. 13/14).
 */
export interface Privacy {
  contact_form_notice: ContactFormNotice;
  controller: ResponsiblePerson;
  controller_contact: ContactDetails;
  cookies_notice: CookiesNotice;
  data_categories: DataCategories;
  data_protection_officer?: DataProtectionOfficer;
  hosting: Hosting;
  last_updated: LastUpdated1;
  legal_basis: LegalBasis;
  no_tracking_notice: NoTrackingNotice;
  recipients: Recipients;
  retention: Retention;
  rights: Rights;
  supervisory_authority: Authority;
}
export interface LegalSection {
  heading: Heading4;
  paragraphs: Paragraphs1;
}
export interface Hosting {
  location: Location;
  note: Note3;
  provider: Provider;
}
export interface Authority {
  address: Address;
  name: Name4;
  url: Url2;
}
export interface MediaSection {
  heading: Heading5;
  images?: Images;
  intro: Intro4;
  videos?: Videos;
}
export interface MediaImage {
  alt: Alt;
  caption?: Caption;
  id: Id;
  src: Src;
  title: Title1;
}
export interface MediaVideo {
  caption?: Caption1;
  id: Id1;
  poster?: Poster;
  src: Src1;
  title: Title2;
}
/**
 * Artifact-level metadata. Not rendered, except the fixture banner (see `is_fixture`).
 */
export interface ContentMeta {
  client_slug: ClientSlug;
  is_fixture: IsFixture;
  note?: Note4;
}
export interface Seo {
  pages: Pages;
}
export interface PageSeo {
  description: Description;
  noindex?: Noindex;
  path: Path;
  title: Title3;
}
export interface ServicesSection {
  heading: Heading6;
  intro: Intro5;
  items: Items1;
  note?: Note5;
}
export interface Service {
  features?: Features;
  icon: Icon1;
  id: Id2;
  paragraphs: Paragraphs2;
  summary: Summary;
  title: Title4;
}
export interface SiteIdentity {
  description: Description1;
  name: Name5;
  og_image?: OgImage;
  short_name?: ShortName;
  tagline: Tagline;
  theme_color: ThemeColor;
  url: Url3;
}
export interface TeamSection {
  heading: Heading7;
  intro: Intro6;
  members: Members;
}
export interface TeamMember {
  bio: Bio;
  focus_areas?: FocusAreas;
  id: Id3;
  languages: Languages;
  name: Name6;
  photo_url?: PhotoUrl;
  qualifications: Qualifications;
  role: Role;
}
