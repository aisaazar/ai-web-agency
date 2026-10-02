import Link from "next/link";

export const dynamic = "force-dynamic";

const templates = [
  {
    id: "health",
    name: "Health / Praxis",
    eyebrow: "Clean medical",
    description: "Bright, calm and clinical. Built for trust, clear services and conversion-focused calls to action.",
    className: "templatePreview healthPreview",
    tags: ["Medical", "Light", "Motion-ready"],
  },
  {
    id: "corporate",
    name: "Corporate / Professional",
    eyebrow: "Executive",
    description: "Structured typography and confident spacing for practices or businesses that want a premium corporate feel.",
    className: "templatePreview corporatePreview",
    tags: ["Professional", "Editorial", "Premium"],
  },
  {
    id: "warm",
    name: "Warm / Human",
    eyebrow: "Hospitality",
    description: "Softer shapes and warmer visual language for clinics that want a more personal, welcoming first impression.",
    className: "templatePreview warmPreview",
    tags: ["Warm", "Human", "Boutique"],
  },
] as const;

export default function TemplatesPage() {
  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Site Studio</div>
          <h1>Template Gallery</h1>
          <div className="muted">Choose the visual direction before the site moves into design.</div>
        </div>
        <Link className="button secondaryButton" href="/clients/new">New client</Link>
      </div>

      <section className="templateGallery" aria-label="Available website templates">
        {templates.map((template) => (
          <article className="templateCard" key={template.id}>
            <div className={template.className} aria-hidden="true">
              <div className="templatePreviewTop"><span /><span /><span /></div>
              <div className="templatePreviewHero">
                <div className="previewKicker">{template.eyebrow}</div>
                <div className="previewHeading">Your next<br />great website.</div>
                <div className="previewLine" />
                <div className="previewButtons"><span /><span /></div>
              </div>
            </div>
            <div className="templateCardBody">
              <div className="templateCardTitleRow">
                <div>
                  <div className="muted mono">{template.id}</div>
                  <h2>{template.name}</h2>
                </div>
                <span className="badge">Ready</span>
              </div>
              <p className="muted">{template.description}</p>
              <div className="templateTags">
                {template.tags.map((tag) => <span key={tag}>{tag}</span>)}
              </div>
              <Link className="button" href={"/clients/new?preset=" + template.id}>Use this style</Link>
            </div>
          </article>
        ))}
      </section>

      <section className="card section templateNote">
        <div>
          <h2 className="sectionTitle">How selection works</h2>
          <p className="muted">The choice is stored with the client intake and used when the design artifact is created. The underlying template remains shared and content-driven.</p>
        </div>
        <Link className="button secondaryButton" href="/clients">View clients</Link>
      </section>
    </>
  );
}

