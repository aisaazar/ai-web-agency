import Image from "next/image";

import { content } from "@/lib/content";
import { SECTION_ANCHORS } from "./SiteHeader";
import { Section, SectionHeading } from "./ui";

export function MediaSection() {
  const media = content.media;
  const images = media?.images ?? [];
  const videos = media?.videos ?? [];
  if (!media || (images.length === 0 && videos.length === 0)) return null;

  return (
    <Section
      id={SECTION_ANCHORS.media}
      labelledBy="media-heading"
      className="bg-surface-muted"
    >
      <SectionHeading id="media-heading" eyebrow="MEDIEN">
        {media.heading}
      </SectionHeading>
      <div className="space-y-4 text-ink-muted">
        {media.intro.map((paragraph) => (
          <p key={paragraph.slice(0, 40)}>{paragraph}</p>
        ))}
      </div>

      {images.length > 0 ? (
        <div className="mt-10 grid gap-6 sm:grid-cols-2">
          {images.map((item) => (
            <figure
              key={item.id}
              className="overflow-hidden rounded-lg border border-line bg-surface"
            >
              <div className="relative aspect-[16/10]">
                <Image
                  src={item.src}
                  alt={item.alt}
                  fill
                  sizes="(max-width: 640px) 100vw, 50vw"
                />
              </div>
              <figcaption className="p-5">
                {" "}
                <h3 className="text-base font-semibold text-ink">
                  {item.title}
                </h3>
                {item.caption ? (
                  <p className="mt-2 text-sm text-ink-muted">{item.caption}</p>
                ) : null}
              </figcaption>
            </figure>
          ))}
        </div>
      ) : null}

      {videos.length > 0 ? (
        <div className="mt-10 grid gap-6 sm:grid-cols-2">
          {videos.map((item) => (
            <figure
              key={item.id}
              className="overflow-hidden rounded-lg border border-line bg-surface"
            >
              <video
                className="aspect-video w-full object-cover"
                controls
                preload="metadata"
                poster={item.poster ?? undefined}
              >
                <source src={item.src} type="video/mp4" />
                Your browser does not support HTML video.
              </video>
              <figcaption className="p-5">
                {" "}
                <h3 className="text-base font-semibold text-ink">
                  {item.title}
                </h3>
                {item.caption ? (
                  <p className="mt-2 text-sm text-ink-muted">{item.caption}</p>
                ) : null}
              </figcaption>
            </figure>
          ))}
        </div>
      ) : null}
    </Section>
  );
}
