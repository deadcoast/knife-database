# Textual Visual Design Research Report

Research frame and how the attached brief was used
Your attached document is most useful as a design brief, not as a source of truth for current Textual behavior. The durable signals in it are clear: you want screen-level visual ownership, deliberate use of TCSS rather than burying styling in Python, motion that is strongest on entrance and restrained at idle, and a workflow grounded in official Textual docs and exemplar projects. I treated the changelog-like metadata and project-specific historical notes as intentionally low-weight, exactly as you instructed, and used the file mainly to calibrate priorities and taste.

The rest of this report therefore prioritizes primary sources from current Textual documentation, official Textual blog posts, the Textual repository, and strong ecosystem examples. Where I make a recommendation that goes beyond the docs, I label it as a design inference rather than an official rule.

What Textual officially gives you for visual design
Textual’s official position is that appearance should be separated from behavior. The CSS guide explicitly says the major advantages of TCSS are separation of “how your app looks” from “how it works,” simpler customization of built-in and third-party widgets, and live style iteration through textual run --dev. The same guide also notes that CSS_PATH can be a list of files, and the App API confirms that multiple CSS files are loaded in order.

Themes are a first-class design system, not an afterthought. The Themes guide says a theme can define up to 11 base colors, which Textual then expands into a broader set of CSS variables, and those variables update automatically when the active theme changes. Textual also supports app-specific design tokens through App.get_theme_variable_defaults, and the textual colors command previews the color system so you can validate palette decisions before you commit them to the app.

State styling is built into the TCSS model. Official CSS selectors cover IDs, classes, descendant and child combinators, and pseudo-classes such as :hover, :focus, :disabled, :light, and :dark. The CSS guide specifically recommends adding and removing CSS classes as the way to change display dynamically at runtime, rather than treating styles as ad hoc imperative code. That is the design-friendly path for focus rings, selection states, reveal states, “active panel” treatments, and progressive disclosure.

Motion is also a documented primitive. The Animation guide says Textual can animate styles such as offset and opacity, that App, Widget, and styles objects all expose animate, and that easing, delays, and completion callbacks are all part of the standard API. Textual even ships a CLI preview for easing curves through textual easing, which is useful when you are formalizing a motion system instead of sprinkling arbitrary timings around the codebase.

Layout is intentionally declarative. The Layout guide and the “Anatomy of a Textual User Interface” post both emphasize that layout is expressed through styles rather than manual geometry math, and that you can compose screens from containers, grids, docking, and stacked screens. One important caveat from the docs: Textual grid is not browser CSS Grid, so web instincts help but should not be transplanted blindly. Docking is especially relevant for polished UIs because it gives you sticky headers, footers, and sidebars that do not scroll away.

A subtle but extremely important official detail: Screen.CSS and Screen.CSS_PATH do not scope styles to just that screen. The Screen API explicitly notes that both apply to the whole app. By contrast, widget DEFAULT_CSS is scoped by default, and Textual’s widget docs and 0.38 release notes explain that scoped CSS exists to stop a widget’s internal rules from leaking into unrelated parts of the UI. In practice, that means “one stylesheet per screen” is absolutely viable for organization, but it only works safely if your selectors are namespaced by a screen type, root ID, or root class.

The styling architecture that fits a serious Textual app
The strongest Textual design architecture is a layered one. At the base, keep a global foundation stylesheet for spacing, elevation, typography, borders, interaction timings, and theme token usage. Above that, keep a widgets stylesheet for reusable patterns and custom widget overrides. Then load screen-specific TCSS files for page-level composition. Officially, App-level CSS_PATH supports multiple files loaded in order, so this structure works cleanly and without fighting the framework.

The critical rule is selector scoping. Because screen stylesheets are global once loaded, each screen file should be written as if it were a mini design namespace. The easiest pattern is to give each screen a root selector—either the screen type itself, an ID, or a class—and scope every rule beneath it. That gives you the maintainability the attached brief wants without accidental cross-screen bleed. This is an inference from the official Screen.CSS_PATH behavior, but it is the safest way to reconcile per-screen ownership with Textual’s actual stylesheet model.

```python

from textual.app import App
from textual.screen import Screen

class ResearchScreen(Screen):
    pass

class MyApp(App):
    CSS_PATH = [
        "styles/foundation.tcss",
        "styles/widgets.tcss",
        "styles/screens/research.tcss",
    ]
```

```tcss

/* research.tcss */
ResearchScreen {
    background: $background;
}

ResearchScreen .hero {
    border: wide $primary;
    background: $primary 10%;
}

ResearchScreen DataTable {
    border: round $panel;
}
```

A second strong pattern is to push custom visual surfaces into widgets rather than into screens. The widget guide recommends DEFAULT_CSS for distributed or self-contained widgets, and that scoped CSS is lower-specificity than app CSS. That combination is ideal for your “impressive asset” surfaces: hero cards, pseudo-terminal panels, status mosaics, animated banners, or bespoke gauges can live as proper widgets with their own internal defaults, while individual screens can still restyle them from outside.

A third pattern is to let classes, not imperative style-setting, drive visual state. The official CSS guide says add_class, remove_class, toggle_class, and set_class are the recommended mechanisms for runtime display changes. This matters because once state is expressed as classes, your visual documentation becomes much clearer: every component can document default, hover, focus, selected, loading, empty, error, and completed states as selector-driven variants.

For emphasis and atmosphere, Textual’s style primitives are richer than many terminal developers assume. opacity is supported, but the docs clarify it is simulated by blending rather than “true” opacity. There is also text-opacity, background-tint, and tint, all of which are useful for subtle hierarchy, modal overlays, deemphasis, and non-destructive state contrast. Used with restraint, these are a better fit for “impressive” than hard-flashing borders or constant motion.

My design inference from both the official docs and your brief is this: Textual should be treated as a system for layered emphasis. Give each screen one hero moment on entry, then rely on smaller focus, hover, selection, and scroll cues afterward. That aligns with the official animation API, the framework’s support for partial updates and smooth scrolling, and your stated preference for noticeable but not overbearing motion.

The highest-value official widgets and visual assets to build around
If the goal is to produce a visually credible, developer-impressive Textual application, the highest-leverage official widgets are the ones that combine strong default affordances with stylable internal parts. TextArea is one of the clearest examples: the official release post describes it as a fully featured code editor with syntax highlighting, line numbers, and a highly configurable appearance. If your app touches code, prompts, queries, notes, or structured input, this should be treated as a flagship surface rather than a plain input field.

Markdown and MarkdownViewer are another major asset. The widget docs describe MarkdownViewer as adding browser-like functionality and an optional table of contents, while the Markdown widget release post highlights scrollable code fences, tables, and link support. That same post also notes you can generate SVG screenshots with textual run my_app.py --screenshot 5, which is extremely valuable for your own design documentation, changelogs, and gallery pages.

DirectoryTree is a strong example of how deep official styling support goes. Its docs expose component classes for file names, folders, hidden items, and extensions. That means “file browser” does not need to mean “unstyled utility sidebar”; it can become a genuine design surface with semantic color, subdued hidden-item treatment, and extension-level accenting.

DataTable is one of the best high-density components for polished TUIs because it exposes component classes for cursor, hover, fixed rows and columns, headers, and odd/even rows. In other words, you are not limited to “plain grid of text”; you can design navigational emphasis, row striping, focus treatments, and header hierarchy directly in TCSS. Textual’s older Markdown release post also notes that the table API gained sorting and cell-update work, which reinforces it as more than a static renderer.

TabbedContent is important when a screen wants sectional density without visual chaos. The docs say it is built from Tabs and ContentSwitcher, and they explicitly show how to style individual tabs by the --content-tab- prefixed IDs derived from TabPane IDs. That makes it a good pattern for “one screen, several related modes” without resorting to modal overload.

For metrics, progress, and lightweight dashboards, ProgressBar and Sparkline are more designable than they first appear. ProgressBar is composed of three stylable sub-widgets, while Sparkline exposes dedicated component classes for low and high values. Together, those let you build status panels and research dashboards that feel intentional instead of improvised.

Finally, when built-ins are close but not enough, Textual’s custom-widget path remains a visual asset rather than a fallback. The widget guide shows that custom widgets can carry DEFAULT_CSS, scoped CSS, rich renderables, and component classes for line-API-driven internals. That is the right way to build pseudo-terminal surfaces, animated headers, waveform-like separators, or card components with intricate internal styling.

What strong terminal projects do well
The best Textual-adjacent projects do not rely on raw ornament; they pair visual clarity with a few memorable surfaces. Toad is a strong current example. Its README presents the app visually from the start, then emphasizes a fully working shell, a Markdown prompt editor with syntax highlighting, a fuzzy file picker with a tree control, “beautiful diffs,” settings, and concurrent sessions. The design lesson is that impressive terminal UI usually comes from giving distinct tasks their own distinctive surface language, not from making every part of the screen equally loud.

Trogon demonstrates a different strength: discoverability and approachability. Its README frames the project as a way to auto-generate friendly terminal interfaces for CLIs, explains the user value as helping people rediscover complex command options, and foregrounds screenshots and a video tour. The lesson for your docs is important: exemplary terminal projects show the UI early and explain the information architecture in plain language, not just the implementation.

Frogmouth is a useful reference for content-first design. The project describes itself as a Markdown viewer/browser with browser-like navigation, history, bookmarks, and table of contents, and it also foregrounds screenshots. Its lesson is that terminal UIs feel premium when reading surfaces are treated with the same respect as action surfaces—clear navigation chrome, body text hierarchy, and a calm content viewport.

Toolong is the best example of “high information density can still feel polished.” The README emphasizes live tailing, syntax highlighting, JSONL support, merge views, screenshots, and videos; the related Textual blog post explains how it stays responsive by reading only the visible portion of large files, scanning line breaks efficiently, and batching work in a worker. Together, those sources suggest a rule worth adopting: design ambition only feels impressive when performance is stable enough that the interface still feels effortless.

Across all four projects, the documentation pattern is consistent: they use screenshots or recordings as first-class explanatory assets, not as marketing afterthoughts. That aligns well with Textual’s own screenshot tooling and snapshot testing support. If your goal is a visually notable Textual project, your repo docs should behave more like a product gallery plus design system than a plain engineering README.

The design rules I would adopt for a Textual visual system
Start with one registered theme and a small number of app-specific variables. Officially, Textual themes already generate a broad variable set from base colors, and the framework lets you add your own tokens. That means your documentation should define semantic tokens such as hero-background, hero-border, panel-muted, focus-glow, danger-soft, and chart-accent instead of hardcoding raw color values in screen files.

Treat motion as a hierarchy. Textual’s animation API is strong enough to support fades, offsets, delays, and easing, and the compositor can perform partial updates efficiently. But the most credible motion system in a terminal is still layered: one entrance animation per screen, directed attention for focus changes, and very light ambient behavior afterward. This is a design inference, but it is supported by the framework’s capabilities and by your own brief’s desire for spectacle without overstimulation.

Use screen stacks and opacity for overlays, not just for navigation. The screens guide explicitly documents modal screens and screen opacity via alpha backgrounds. That combination is ideal for elegant confirmations, detail drawers, spotlight cards, and “inspect” overlays that leave context visible underneath. It is a more polished pattern than tearing the user away from the current screen or replacing the entire interface for every secondary task.

Prefer official widgets until you can articulate a real reason not to. Textual already ships a large widget inventory, from buttons and trees to text editors, tab systems, markdown viewers, tables, progress bars, and sparklines. If a component already exists and exposes stylable component classes or sub-widgets, use it first and push it hard stylistically before reaching for custom drawing. Save bespoke widgets for the places where you want a signature surface.

Make browser and terminal preview part of the same design workflow. The devtools guide says textual serve can present apps in a browser and that textual run --dev gives live CSS editing. That means a serious visual workflow in Textual is not “edit, rerun, guess.” It is “edit live, preview fast, capture screenshots, then lock design with snapshot tests.”

The essential documentation set I would create in your repository
Design principles should explain the visual thesis of the app: what each screen is for, how much emphasis it deserves, what “hero,” “supporting,” and “ambient” motion mean, and how contrast, density, and retro or industrial accents are supposed to be balanced. That document should explicitly state that Textual’s official theme variables and TCSS architecture are the source of truth for implementation.

Styling architecture should document the file layout and selector strategy: foundation styles, widget styles, and screen styles; the fact that App.CSS_PATH can load multiple files in order; and the non-obvious warning that Screen.CSS_PATH still applies globally unless selectors are namespaced. This is the document that prevents style drift later.

Theme and token catalog should list your semantic variables, map them to Textual theme variables where possible, and note which tokens are allowed in which contexts. Officially, Textual already provides built-in variables plus app-specific variable extension points, so this document becomes the contract between design intent and implementation.

Screen specs should exist one per screen. Each spec should record the screen’s purpose, primary built-in widgets, layout model, interaction states, entrance motion, ambient motion, focus behavior, empty/error/loading variants, and the exact root selector that scopes its TCSS. This mirrors how strong Textual projects differentiate their major surfaces and is the most direct way to achieve the “page owns its presentation” model your brief calls for.

Component inventory should cover all reused pieces: custom widgets, built-in widgets with heavy styling, and any widget that exposes component classes. Include the selectors you rely on, the state classes they support, and screenshot examples for default, focus, hover, and active states. Textual’s widget docs make this feasible because component classes are explicitly documented for many high-value widgets.

Visual QA workflow should formalize how you iterate and how you lock designs. It should reference textual run --dev for live CSS editing, textual serve for browser preview, SVG screenshot generation for docs, and snapshot testing for regression control. The testing guide explicitly says Textual uses snapshot testing internally for built-in widgets, which is exactly the standard you want if visual quality is part of the product, not decoration.

The short version is this: Textual already has the right primitives for serious visual design. The constraint is not capability; it is discipline. The official docs support a workflow built around theme tokens, layered TCSS, screen namespacing, component classes, documented motion, live iteration, browser preview, and screenshot-based regression testing. If you build your documentation around those mechanics—and around the task-focused visual lessons from Toad, Trogon, Frogmouth, and Toolong—you will have a Textual design system that feels both ambitious and coherent.
