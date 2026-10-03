# Looks

Looks is an open design system for e-ink dashboards: five complete page styles for code
elements. A code element built from its components takes one look from a single attribute, and
reads at every panel size, in colour and on one-bit panels. In code the library keeps its original
name, Mosaic: the global is `Mosaic`, the classes start with `m-`, and the source lives at
[dmellok/tesserae-mosaic](https://github.com/dmellok/tesserae-mosaic). (A Mosaic layout, in the
cloud editor, is a dashboard made of widget tiles; the two are unrelated.)

| Look | What it is |
|---|---|
| `bauhaus` | Solid colour blocks, thick rules, very heavy type and big icons. |
| `almanac` | A printed page: serif numerals, a masthead between rules, one red accent. |
| `signal` | Swiss minimal on a twelve-column grid, designed for one-bit panels first. |
| `pixel` | Pixel type, pixel-art icons and dithered windows. |
| `os7` | The classic Macintosh System 7: pinstriped windows, a menu bar, dialogs. |

It is optional. A code element opts in by using it: a `data-look`, Mosaic's classes, or a call to
`Mosaic.`. Tesserae then inlines the core, that look, the script, the look's fonts and its icons.

```html
<main class="m" data-look="almanac"><div class="m-page">
  <header class="m-masthead"><span>Tuesday</span><span>29 September</span><span>2026</span></header>
  <div class="m-hero"><div class="m-clock" data-fit></div></div>
</div></main>
```

```js
Mosaic.clock(document.querySelector(".m-clock"));
Mosaic.ready();   // loads the look's fonts, then fits [data-fit] text and trims lists
```

The components, tokens and script are documented in the
[Mosaic README](https://github.com/dmellok/tesserae-mosaic#readme). To update the vendored copy,
build Mosaic and run `python3 scripts/sync_mosaic.py`.
