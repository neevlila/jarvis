"""
Creative Direction & Design Systems Engine for J.A.R.V.I.S.

Determines domain-grounded visual identity, color palettes, typography hierarchy,
motion strategy, and strictly justified 3D usage for project blueprints.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import re

from idea_engine.models import ProjectIdea, VisualDirection, MotionLevel, ThreeDIntensity


@dataclass
class ColorPalette:
    primary: str
    secondary: str
    background: str
    surface: str
    text_primary: str
    text_muted: str
    accent: str
    border: str
    success: str
    warning: str
    error: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "primary": self.primary,
            "secondary": self.secondary,
            "background": self.background,
            "surface": self.surface,
            "text_primary": self.text_primary,
            "text_muted": self.text_muted,
            "accent": self.accent,
            "border": self.border,
            "success": self.success,
            "warning": self.warning,
            "error": self.error
        }


@dataclass
class TypographySystem:
    heading_font: str
    body_font: str
    mono_font: str
    weights: str
    scale_notes: str


@dataclass
class ThreeDStrategy:
    is_justified: bool
    recommended_tech: str
    scene_description: str
    interaction_model: str
    mobile_fallback: str


@dataclass
class MotionStrategy:
    motion_level: str
    functional_rules: List[str]
    decorative_rules: List[str]
    easing_and_timing: str
    reduced_motion_rule: str


@dataclass
class CreativeDesignSpec:
    visual_direction: str
    theme_description: str
    palette: ColorPalette
    typography: TypographySystem
    threed_strategy: ThreeDStrategy
    motion_strategy: MotionStrategy
    component_styling_rules: List[str]


class CreativeDirector:
    """
    Synthesizes custom visual identities, design systems, and interaction models
    grounded in the specific domain and requirements of a project blueprint.
    """

    DOMAIN_PALETTES = {
        "cybersecurity": ColorPalette(
            primary="#00d2ff",
            secondary="#0055ff",
            background="#040608",
            surface="#0b1118",
            text_primary="#f0f6fc",
            text_muted="#6e7681",
            accent="#00ffcc",
            border="rgba(0, 210, 255, 0.2)",
            success="#00ffcc",
            warning="#ffaa00",
            error="#ff3b30"
        ),
        "fintech": ColorPalette(
            primary="#10b981",
            secondary="#047857",
            background="#090d16",
            surface="#111827",
            text_primary="#f9fafb",
            text_muted="#9ca3af",
            accent="#34d399",
            border="rgba(16, 185, 129, 0.15)",
            success="#10b981",
            warning="#f59e0b",
            error="#ef4444"
        ),
        "healthcare": ColorPalette(
            primary="#0284c7",
            secondary="#0369a1",
            background="#0a101d",
            surface="#0f172a",
            text_primary="#f8fafc",
            text_muted="#64748b",
            accent="#38bdf8",
            border="rgba(56, 189, 248, 0.18)",
            success="#22c55e",
            warning="#eab308",
            error="#f43f5e"
        ),
        "devtools": ColorPalette(
            primary="#6366f1",
            secondary="#4f46e5",
            background="#0b0f19",
            surface="#151b2b",
            text_primary="#f3f4f6",
            text_muted="#9ca3af",
            accent="#a855f7",
            border="rgba(99, 102, 241, 0.2)",
            success="#10b981",
            warning="#f59e0b",
            error="#ef4444"
        ),
        "ai_ml": ColorPalette(
            primary="#8b5cf6",
            secondary="#6d28d9",
            background="#060813",
            surface="#0e1329",
            text_primary="#f8fafc",
            text_muted="#818cf8",
            accent="#c084fc",
            border="rgba(139, 92, 246, 0.25)",
            success="#10b981",
            warning="#fbbf24",
            error="#f87171"
        ),
        "agriculture": ColorPalette(
            primary="#84cc16",
            secondary="#4d7c0f",
            background="#0c120a",
            surface="#141f10",
            text_primary="#f7fee7",
            text_muted="#84a98c",
            accent="#a3e635",
            border="rgba(132, 204, 22, 0.2)",
            success="#84cc16",
            warning="#f59e0b",
            error="#ef4444"
        ),
        "automotive": ColorPalette(
            primary="#e11d48",
            secondary="#9f1239",
            background="#0a0a0c",
            surface="#141418",
            text_primary="#ffffff",
            text_muted="#71717a",
            accent="#fb7185",
            border="rgba(225, 29, 72, 0.2)",
            success="#22c55e",
            warning="#f59e0b",
            error="#e11d48"
        ),
        "creative": ColorPalette(
            primary="#f43f5e",
            secondary="#e11d48",
            background="#09090b",
            surface="#18181b",
            text_primary="#fafafa",
            text_muted="#a1a1aa",
            accent="#ec4899",
            border="rgba(244, 63, 94, 0.2)",
            success="#10b981",
            warning="#f59e0b",
            error="#f43f5e"
        ),
        "default": ColorPalette(
            primary="#00d2ff",
            secondary="#3b82f6",
            background="#070b12",
            surface="#0e1726",
            text_primary="#f8fafc",
            text_muted="#94a3b8",
            accent="#38bdf8",
            border="rgba(0, 210, 255, 0.18)",
            success="#00ffcc",
            warning="#f59e0b",
            error="#ef4444"
        )
    }

    @classmethod
    def analyze_design(
        cls,
        idea: ProjectIdea,
        requested_visual: VisualDirection = VisualDirection.AUTO,
        requested_motion: MotionLevel = MotionLevel.BALANCED,
        requested_3d: ThreeDIntensity = ThreeDIntensity.AUTO
    ) -> CreativeDesignSpec:
        """
        Determines the complete creative specification for an idea blueprint.
        """
        combined_text = f"{idea.title} {idea.one_line_pitch} {idea.problem} {idea.solution} {' '.join(idea.core_features)}".lower()

        # 1. Infer Domain & Visual Direction
        def has_any(keywords: List[str]) -> bool:
            return any(re.search(r"\b" + re.escape(w) + r"\b", combined_text, re.IGNORECASE) for w in keywords)

        domain_key = "default"
        if has_any(["security", "vulnerability", "auth", "threat", "firewall", "cyber", "cybersecurity", "malware", "penetration", "soc2"]):
            domain_key = "cybersecurity"
            inferred_visual = "Dark Technical Cybersecurity HUD with Network Topologies"
        elif has_any(["farm", "crop", "crops", "agriculture", "agricultural", "soil", "harvest", "plant", "climate", "farming", "agritech"]):
            domain_key = "agriculture"
            inferred_visual = "Organic Eco-Data Interface with Terrain Depth and Natural Hues"
        elif has_any(["car", "cars", "vehicle", "vehicles", "automotive", "telemetry", "engine", "autonomous driving", "racing", "tire"]):
            domain_key = "automotive"
            inferred_visual = "Cinematic High-Performance Automotive Interface with 3D Telemetry"
        elif has_any(["finance", "fintech", "payment", "bank", "crypto", "trading", "investment", "invoice", "ledger"]):
            domain_key = "fintech"
            inferred_visual = "Minimal Precision Fintech Aesthetic with High Data-Density"
        elif has_any(["health", "medical", "patient", "clinical", "doctor", "hospital", "pharma", "biotech"]):
            domain_key = "healthcare"
            inferred_visual = "Clean Clinical Bio-Tech Interface with Calm Visual Cadence"
        elif has_any(["ai", "neural", "llm", "vision", "model", "inference", "prompt", "agent", "cognitive"]):
            domain_key = "ai_ml"
            inferred_visual = "Futuristic Cognitive AI Canvas with Particle Gradients and Glass Overlays"
        elif has_any(["code", "developer", "git", "api", "terminal", "debugger", "ide", "cli", "compiler"]):
            domain_key = "devtools"
            inferred_visual = "Engineered High-Contrast DevTool Interface with Rich Code Panes"
        elif has_any(["music", "art", "creative", "design", "video", "media", "portfolio"]):
            domain_key = "creative"
            inferred_visual = "Expressive Editorial Showcase with Asymmetric Layouts and Rich Media"
        else:
            inferred_visual = "Modern Dark Glassmorphic Enterprise Application"

        # Override visual direction if user requested explicit style
        if requested_visual != VisualDirection.AUTO:
            visual_direction_str = requested_visual.value
        else:
            visual_direction_str = inferred_visual

        palette = cls.DOMAIN_PALETTES.get(domain_key, cls.DOMAIN_PALETTES["default"])

        # 2. Typography Selection
        if domain_key in ["cybersecurity", "devtools"]:
            typography = TypographySystem(
                heading_font="Space Grotesk, system-ui, sans-serif",
                body_font="Inter, -apple-system, BlinkMacSystemFont, sans-serif",
                mono_font="JetBrains Mono, Fira Code, monospace",
                weights="Headings: 600/700 | Body: 400/500 | Code/Stats: 600",
                scale_notes="Dense information hierarchy with crisp 11px-13px mono labels and prominent 24px-32px section headers."
            )
        elif domain_key in ["fintech", "healthcare"]:
            typography = TypographySystem(
                heading_font="Plus Jakarta Sans, system-ui, sans-serif",
                body_font="Inter, -apple-system, BlinkMacSystemFont, sans-serif",
                mono_font="JetBrains Mono, monospace",
                weights="Headings: 700 | Body: 400/500 | Numeric Data: 600 (tabular figures)",
                scale_notes="High legibility typography with strict tabular numerical alignment for financial/clinical metrics."
            )
        elif domain_key in ["creative", "editorial"]:
            typography = TypographySystem(
                heading_font="Fraunces, Playfair Display, serif",
                body_font="Inter, -apple-system, BlinkMacSystemFont, sans-serif",
                mono_font="JetBrains Mono, monospace",
                weights="Headings: 500/800 | Body: 400/500",
                scale_notes="Editorial typographic contrast combining expressive serif headlines with ultra-clean sans-serif body copy."
            )
        else:
            typography = TypographySystem(
                heading_font="Space Grotesk, Plus Jakarta Sans, sans-serif",
                body_font="Inter, system-ui, sans-serif",
                mono_font="JetBrains Mono, monospace",
                weights="Headings: 600/700 | Body: 400/500",
                scale_notes="Balanced modern SaaS typography with high contrast headings and comfortable body leading."
            )

        # 3. 3D Justification Strategy
        # Strictly require explicit 3D / spatial / topology / CAD / digital twin concepts to justify heavy WebGL rendering
        has_3d_need = any(re.search(r"\b" + re.escape(w) + r"\b", combined_text, re.IGNORECASE) for w in [
            "3d", "threejs", "three.js", "webgl", "spatial", "mesh", "topology", "cad",
            "volumetric", "lidar", "photogrammetry", "digital twin", "vr", "ar",
            "physics engine"
        ])

        if requested_3d == ThreeDIntensity.NONE:
            threed_strat = ThreeDStrategy(
                is_justified=False,
                recommended_tech="CSS 3D Transforms / Subtle layered 2D depth",
                scene_description="No WebGL canvas needed. Use clean 2D layered surfaces with soft shadows for elevation.",
                interaction_model="Elevation and hover translation along Z-axis.",
                mobile_fallback="Standard 2D flat layout."
            )
        elif requested_3d == ThreeDIntensity.IMMERSIVE or (requested_3d == ThreeDIntensity.AUTO and has_3d_need):
            threed_strat = ThreeDStrategy(
                is_justified=True,
                recommended_tech="Three.js / React Three Fiber / WebGL Shaders",
                scene_description=f"Interactive 3D visualization representing {idea.title} domain structures (e.g. interactive node network or spatial telemetry).",
                interaction_model="OrbitControls with smooth damping, hover raycasting on interactive nodes, and camera fly-to animations on selection.",
                mobile_fallback="Downscaled particle count or interactive SVG topology with touch gesture support."
            )
        elif requested_3d == ThreeDIntensity.MODERATE:
            threed_strat = ThreeDStrategy(
                is_justified=True,
                recommended_tech="Spline 3D / Lightweight Three.js canvas",
                scene_description="Focused 3D hero model or interactive floating device/component canvas with ambient lighting.",
                interaction_model="Mouse parallax tilt with bounded rotation angles (max 15deg).",
                mobile_fallback="Static rendered WebP frame with CSS glow fallback."
            )
        else:
            # Default / Subtle: Avoid forcing heavy 3D if not justified
            threed_strat = ThreeDStrategy(
                is_justified=False,
                recommended_tech="CSS 3D Transforms & Canvas 2D Particles",
                scene_description="Lightweight depth layers and ambient particle field to maintain 60 FPS without WebGL overhead.",
                interaction_model="Subtle cursor-following parallax on card containers.",
                mobile_fallback="Static backdrop with gradient overlays."
            )

        # 4. Motion Strategy
        motion_lvl_str = requested_motion.value if isinstance(requested_motion, MotionLevel) else str(requested_motion)
        
        functional_rules = [
            "State changes (expand, collapse, modal open) MUST communicate hierarchy and direct cause-and-effect.",
            "List items and table rows MUST use subtle staggered reveals (20ms-40ms stagger) on initial render.",
            "Interactive buttons MUST provide instant haptic visual feedback (< 100ms micro-scale to 0.98).",
            "Loading skeletons and async updates MUST transition smoothly with opacity cross-fades (150ms-250ms)."
        ]
        
        if requested_motion in [MotionLevel.CINEMATIC, MotionLevel.EXPERIMENTAL]:
            decorative_rules = [
                "Scroll-driven storytelling with multi-layer parallax depth transitions.",
                "Smooth camera fly-through sequences linking core section reveals.",
                "Ambient glow pulsations reacting to data throughput and user activity."
            ]
            easing = "cubic-bezier(0.16, 1, 0.3, 1) [Smooth Exponential Out]"
        elif requested_motion == MotionLevel.SUBTLE:
            decorative_rules = [
                "Zero distracting ambient loops. Motion restricted strictly to user interactions."
            ]
            easing = "cubic-bezier(0.4, 0, 0.2, 1) [Standard Material Fast]"
        else: # BALANCED
            decorative_rules = [
                "Subtle backdrop illumination shifts and gentle card hover elevations (+4px Y translation).",
                "Progressive bar and gauge fills animating on viewport intersection."
            ]
            easing = "cubic-bezier(0.25, 1, 0.5, 1) [Snappy Precision Curve]"

        motion_strat = MotionStrategy(
            motion_level=motion_lvl_str,
            functional_rules=functional_rules,
            decorative_rules=decorative_rules,
            easing_and_timing=easing,
            reduced_motion_rule="@media (prefers-reduced-motion: reduce) { *, ::before, ::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; } }"
        )

        component_rules = [
            f"Cards: Background {palette.surface}, border 1px solid {palette.border}, 12px-16px border-radius with subtle 0 8px 32px backdrop shadow.",
            f"Primary Buttons: Solid {palette.primary} background, dark high-contrast typography, 0 0 16px glow on hover.",
            f"Secondary Buttons: Transparent surface, 1px solid {palette.border}, text {palette.accent}.",
            f"Inputs: Background rgba(0, 0, 0, 0.4), 1px solid {palette.border}, focus glow border in {palette.accent}."
        ]

        return CreativeDesignSpec(
            visual_direction=visual_direction_str,
            theme_description=f"Tailored visual architecture for {idea.title} in the {domain_key.capitalize()} domain.",
            palette=palette,
            typography=typography,
            threed_strategy=threed_strat,
            motion_strategy=motion_strat,
            component_styling_rules=component_rules
        )
