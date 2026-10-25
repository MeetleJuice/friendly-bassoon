"""Reproduce original README artwork and sanitized 0.19 aggregate charts.

Uses Matplotlib only; no app dependency, user trace, model call or external image.
Run with a Python environment containing Matplotlib, from any directory.
"""

from pathlib import Path
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Polygon

OUT = Path(__file__).parent / "assets"
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "none", "pdf.fonttype": 42})


def label(fig, x, y, text, size, color, weight="normal", **kwargs):
    fig.text(x, y, text, fontsize=size, color=color, weight=weight, **kwargs)


def save(fig, name):
    for ext in ("svg", "png"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)


def emblem(ax, symbol, color):
    ax.set(xlim=(-1.3, 1.3), ylim=(-1.3, 1.3), aspect="equal")
    ax.axis("off")
    ax.add_patch(Circle((0, 0), 1.1, facecolor="none", edgecolor=color, alpha=.18, linewidth=1))
    if symbol == "orion":
        ax.add_patch(Polygon([(-.65, -.35), (-.85, .5), (-.35, .1), (0, .85),
                             (.35, .1), (.85, .5), (.65, -.35)],
                            fill=False, edgecolor=color, linewidth=2.6, joinstyle="round"))
        ax.plot([-.65, .65], [-.65, -.65], color=color, linewidth=2.6)
        ax.add_patch(Polygon([(0, .2), (.16, -.05), (0, -.3), (-.16, -.05)],
                            facecolor=color, edgecolor="none"))
    elif symbol == "scout":
        ax.add_patch(Circle((-.12, .16), .58, fill=False, edgecolor=color, linewidth=2.6))
        ax.plot([.32, .82], [-.28, -.82], color=color, linewidth=4, solid_capstyle="round")
        ax.add_patch(Circle((-.12, .16), .17, color=color, alpha=.7))
    elif symbol == "ada":
        vertices = []
        for i in range(48):
            theta = 2 * math.pi * i / 48
            r = .95 if i % 4 in (0, 1) else .75
            vertices.append((r * math.cos(theta), r * math.sin(theta)))
        ax.add_patch(Polygon(vertices, fill=False, edgecolor=color, linewidth=2))
        ax.add_patch(Circle((0, 0), .44, fill=False, edgecolor=color, linewidth=2))
        ax.add_patch(Polygon([(0, .32), (.12, .10), (.32, 0), (.12, -.10),
                             (0, -.32), (-.12, -.10), (-.32, 0), (-.12, .10)], color=color))
    elif symbol == "vera":
        ax.add_patch(Polygon([(0, 1), (.65, 0), (0, -1), (-.65, 0)],
                            fill=False, edgecolor=color, linewidth=2.6))
        ax.plot([0, -.25, 0, .25, 0], [1, 0, -1, 0, 1], color=color, linewidth=1.5)
        ax.plot([-.65, .65], [0, 0], color=color, linewidth=1.5)
    elif symbol == "sentinel":
        ax.add_patch(Polygon([(-.78, .65), (0, 1), (.78, .65), (.64, -.38),
                             (0, -1), (-.64, -.38)],
                            fill=False, edgecolor=color, linewidth=2.6, joinstyle="round"))
        ax.add_patch(Polygon([(0, .56), (.28, 0), (0, -.56), (-.28, 0)], color=color, alpha=.85))
    elif symbol == "atlas":
        t = [2 * math.pi * i / 200 for i in range(201)]
        ax.plot([.92 * math.cos(v) for v in t], [.67 * math.sin(2*v) for v in t],
                color=color, linewidth=3)
        ax.scatter([0], [.98], s=25, marker="*", c=color)


def banner():
    bg, fg, muted = "#0D1528", "#F3F6FF", "#A4B2CE"
    fig = plt.figure(figsize=(16, 5), facecolor=bg)
    label(fig, .045, .865, "AIGENTICS", 35, fg, "bold")
    label(fig, .047, .785, "THE MIDNIGHT CREW", 13, "#97B9FF", "bold")
    label(fig, .955, .88, "LOCAL AGENTS. VISIBLE EVIDENCE.", 12, fg, "bold", ha="right")
    label(fig, .955, .81, "Build carefully. Verify the work. Keep what we learn.", 11, muted, ha="right")
    roster = [("ORION", "Coordinator", "#7BA7FF"), ("SCOUT", "Investigator", "#25D9CD"),
              ("ADA", "Builder", "#F2B552"), ("VERA", "Test engineer", "#C39AF2"),
              ("SENTINEL", "Reviewer", "#EF748A"), ("ATLAS", "Continuity", "#9E97FF")]
    for i, (name, role, color) in enumerate(roster):
        x = .045 + i * .154
        fig.add_artist(FancyBboxPatch((x, .105), .140, .565, transform=fig.transFigure,
            boxstyle="round,pad=0.006,rounding_size=0.025", facecolor="#121F36",
            edgecolor=color, alpha=.7, linewidth=.7, zorder=0))
        emblem(fig.add_axes([x+.025, .295, .09, .29]), name.lower(), color)
        label(fig, x+.070, .225, name, 14, color, "bold", ha="center")
        label(fig, x+.070, .16, role, 10, muted, ha="center")
    save(fig, "midnight-crew-banner")


def results():
    bg, ink, muted = "#F1F5FA", "#192840", "#52657D"
    teal, blue, red = "#008C7C", "#306BD9", "#C84D60"
    fig = plt.figure(figsize=(16, 8.5), facecolor=bg)
    label(fig, .045, .94, "REAL RUNS. RECORDED EVIDENCE.", 13, teal, "bold")
    label(fig, .045, .878, "The 0.19 local test snapshot", 28, ink, "bold")
    label(fig, .045, .833, "Focused campaign • 8B-class local model • Completed in 9m 42s", 12, muted)
    for x, number, title, color in [(.06, "29/29", "App checks passed", teal),
                                    (.29, "20/24", "Agent trials passed", blue),
                                    (.52, "53/53", "Outcomes recorded", teal),
                                    (.75, "2/2", "Orion → Ada runs passed", blue)]:
        label(fig, x, .729, number, 31, color, "bold")
        label(fig, x, .686, title, 11, muted)

    label(fig, .06, .60, "Matched thinking-mode comparison", 16, ink, "bold")
    label(fig, .06, .565, "Default: 5/9 passed     Thinking off: 9/9 passed", 11, muted)
    ax = fig.add_axes([.14, .27, .34, .25], facecolor=bg)
    names, default, off, den = ["Vera", "Scout", "Sentinel", "Unicode"], [1, 1, 1, 2], [3, 2, 2, 2], [3, 2, 2, 2]
    for i, n in enumerate(den):
        for value, delta, color in [(default[i], -.16, "#AAB9CF"), (off[i], .16, teal)]:
            ax.barh(i+delta, value/n*100, height=.27, color=color)
            ax.text(value/n*100+2, i+delta, f"{value}/{n}", va="center", fontsize=10, color=ink)
    ax.set_yticks(range(4), names, fontsize=11)
    ax.set_xticks([0, 50, 100], ["0%", "50%", "100%"])
    ax.set_xlim(0, 118); ax.invert_yaxis()
    ax.tick_params(length=0, labelcolor=muted)
    for spine in ax.spines.values():
        spine.set_visible(False)
    label(fig, .14, .213, "● Default", 10, "#7488A4")
    label(fig, .28, .213, "● Thinking off", 10, teal)

    label(fig, .57, .60, "Four failures. Clear next targets.", 16, ink, "bold")
    for y, count, name, problem in [(.50, "2", "VERA", "Saved correct output; skipped final readback."),
                                    (.40, "1", "SCOUT", "Answered without required source reads."),
                                    (.30, "1", "SENTINEL", "Read sources; cited the wrong line number.")]:
        label(fig, .57, y, count, 29, red, "bold")
        label(fig, .61, y+.013, name, 11, ink, "bold")
        label(fig, .61, y-.022, problem, 10, muted)
    label(fig, .57, .213, "Vera also recovered from 4 rejected JSON proposals.", 11, teal, "bold")
    label(fig, .045, .125, "Scope matters: small repeated scenarios; both Sentinel off passes needed feedback. No full six-agent team result is claimed.", 11, muted)
    label(fig, .045, .084, "Orion delegated to Ada; Sentinel was not dispatched in those runs. Direct Ada also passed 2/2 with fewer model requests.", 11, muted)
    label(fig, .045, .043, "Source: sanitized RESULTS_0190_REVIEW.md • historical baseline, not a prediction or a 0.20 result", 10, muted)
    save(fig, "results-0190")


if __name__ == "__main__":
    banner()
    results()
    print(OUT)
