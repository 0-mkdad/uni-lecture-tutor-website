# Uni Lecture Tutor

The official website for Uni Lecture Tutor, an independent study aid for university lectures in ChatGPT. It introduces the learning workflow and publishes the project's support, privacy, terms and publisher information.

[Website](https://0-mkdad.github.io/uni-lecture-tutor-website/) · [Support](https://0-mkdad.github.io/uni-lecture-tutor-website/support.html) · [Privacy](https://0-mkdad.github.io/uni-lecture-tutor-website/privacy.html) · [Terms](https://0-mkdad.github.io/uni-lecture-tutor-website/terms.html)

## How the product works

Students share lecture materials in ChatGPT and work through explanations, source-grounded notes, practice questions and review checkpoints. The optional MCP tool calculates page coverage from a total page count and a list of page numbers. Read the [privacy notice](https://0-mkdad.github.io/uni-lecture-tutor-website/privacy.html) for details on lecture files, request metadata and service providers.

## Website structure

| Path | Purpose |
| --- | --- |
| `index.html` | English homepage and default entry point |
| `support.html`, `privacy.html`, `terms.html`, `legal.html` | English support and legal pages |
| `de/`, `ar/` | German and Arabic equivalents, with right-to-left layout for Arabic |
| `style.css`, `assets/` | Shared styles and local branding |
| `sitemap.xml`, `robots.txt`, `.nojekyll` | Search discovery and static hosting |

## Preview locally

From the repository root, start a static server:

```sh
python -m http.server 8000
```

Open [localhost:8000](http://localhost:8000). The site needs no build step, runtime dependencies or account to preview. It follows the browser's light or dark preference.

## Maintenance and deployment

- Update corresponding English, German and Arabic pages together. Keep privacy and legal statements consistent across languages.
- Preserve the existing root URLs for the homepage, support, privacy and terms because the plugin metadata references them.
- For new pages, update canonical and language-alternate URLs and the sitemap. Keep internal links relative to support the GitHub Pages repository subpath.
- Check keyboard navigation, narrow and wide layouts, Arabic text direction, both color schemes and links before publishing.
- GitHub Pages serves the root of `main`. After a change reaches `main`, check the Pages deployment and open the public URLs to confirm the update is live.

## Contact

Contact [Mohammad Almekdad](https://mkdad.de/) at [info@mkdad.de](mailto:info@mkdad.de). For support requests, include the version, relevant steps and a short redacted example.
