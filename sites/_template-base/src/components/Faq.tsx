import { content } from "@/lib/content";
import { SECTION_ANCHORS } from "./SiteHeader";
import { Paragraphs, Section, SectionHeading } from "./ui";

/**
 * FAQ. Uses native <details>/<summary>: accessible and keyboard-operable with zero JavaScript.
 * The same items feed the FAQPage JSON-LD, so structured data matches the visible text.
 */
export function Faq() {
  const { faq } = content;

  return (
    <Section id={SECTION_ANCHORS.faq} labelledBy="faq-heading" className="bg-surface-muted">
      <SectionHeading id="faq-heading">{faq.heading}</SectionHeading>
      {faq.intro ? <Paragraphs items={[faq.intro]} /> : null}

      <div className="mt-8 space-y-3">
        {faq.items.map((item) => (
          <details key={item.question} className="rounded-lg border border-line bg-surface p-4">
            <summary className="flex min-h-6 cursor-pointer items-center text-base font-semibold text-ink">
              {item.question}
            </summary>
            <div className="mt-3 space-y-3 text-ink-muted">
              {item.answer.map((paragraph) => (
                <p key={paragraph.slice(0, 40)}>{paragraph}</p>
              ))}
            </div>
          </details>
        ))}
      </div>
    </Section>
  );
}
