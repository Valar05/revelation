shader_type canvas_item;

// ------------------- DISSOLVE PARAMS -------------------
uniform float dissolve_progress : hint_range(0.0, 1.0) = 0.0;
uniform float dissolve_noise_scale : hint_range(0.01, 8.0) = 1.0;
uniform sampler2D dissolve_noise_tex : hint_default_black;
uniform vec2 dissolve_noise_offset = vec2(0.0, 0.0);

float get_noise(vec2 uv) {
    return texture(dissolve_noise_tex, uv / dissolve_noise_scale + dissolve_noise_offset).r;
}

// ------------------- GLOW PARAMS -----------------------
uniform float glow_radius : hint_range(0.0, 64.0) = 6.0;
uniform vec4 glow_color : source_color = vec4(1.0, 1.0, 1.0, 1.0);
// Outline gradient: inner (near sprite) to outer (farther out)
uniform vec4 outline_color_inner : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform vec4 outline_color_outer : source_color = vec4(1.0, 1.0, 1.0, 0.0);
uniform vec4 modulate_color : source_color = vec4(1.0, 1.0, 1.0, 1.0);
// Optional gradient remap: when enabled, the sprite's grayscale (luma)
// is mapped through this gradient texture (U = luma). If disabled or
// the gradient is unassigned (default white), the original color is used.
uniform bool use_gradient_remap = false;
uniform sampler2D gradient_tex : hint_default_white;

// ------------------- SIZE & STRETCH --------------------
uniform float overall_size : hint_range(0.25, 3.0) = 1.0;

// 0.0 = no stretch, 1.0 = top is 2x width
uniform float top_stretch : hint_range(-2.0, 2.0) = 0.0;
// Bottom widen (horizontal) near bottom edge
uniform float bottom_stretch : hint_range(-2.0, 2.0) = 0.0;
// Left / Right widen (vertical) near left/right edges
uniform float left_stretch : hint_range(-2.0, 2.0) = 0.0;
uniform float right_stretch : hint_range(-2.0, 2.0) = 0.0;
// Per-side falloff controls (how quickly effect decays toward center)
uniform float top_falloff : hint_range(0.01, 1.0) = 0.5;
uniform float bottom_falloff : hint_range(0.01, 1.0) = 0.5;
uniform float left_falloff : hint_range(0.01, 1.0) = 0.5;
uniform float right_falloff : hint_range(0.01, 1.0) = 0.5;
uniform float black_threshold : hint_range(0.0, 0.5) = 0.05;

// Deform UV combining per-side stretch influences. This operates in UV
// space so the mesh topology is unchanged and artifacts from vertex edits
// are avoided. The deformation is symmetric around the center for each axis.
vec2 deform_uv(vec2 uv) {
    // center in UV coordinates
    vec2 center = vec2(0.5, 0.5);

    // Compute influence factors in [0,1] per side based on UV distance from edge
    float top_infl = clamp((1.0 - uv.y) / max(0.0001, top_falloff), 0.0, 1.0);
    float bottom_infl = clamp((uv.y) / max(0.0001, bottom_falloff), 0.0, 1.0);
    float left_infl = clamp((1.0 - uv.x) / max(0.0001, left_falloff), 0.0, 1.0);
    float right_infl = clamp((uv.x) / max(0.0001, right_falloff), 0.0, 1.0);

    // Horizontal scale factor applied to x-from-center. Base = 1.0
    float sx = 1.0;
    sx += top_stretch * top_infl;
    sx += bottom_stretch * bottom_infl;

    // Vertical scale factor applied to y-from-center. Base = 1.0
    float sy = 1.0;
    sy += left_stretch * left_infl;
    sy += right_stretch * right_infl;

    // Map uv to centered coordinates, apply scale, map back
    vec2 from_center = uv - center;
    from_center.x *= sx;
    from_center.y *= sy;
    vec2 out_uv = center + from_center;

    // Avoid sampling outside texture 
    out_uv = clamp(out_uv, vec2(0.0), vec2(1.0));
    return out_uv;
}

// ------------------- VERTEX ----------------------------
void vertex() {
    // Sprite2D with centered pivot:
    // VERTEX is already around (0,0) in local space.
    vec2 tex_size = vec2(1.0) / TEXTURE_PIXEL_SIZE;
    vec2 center = tex_size * 0.5;

    // Recenter around texture center, scale, then put back
    vec2 local = VERTEX - center;
    local *= overall_size;
    VERTEX = center + local;
}

// ------------------- FRAGMENT --------------------------
void fragment() {
    // Use deformed UV for sampling
    vec2 uv = deform_uv(UV);

    vec4 base = texture(TEXTURE, uv);
    // Optional gradient remap based on grayscale luma of the sampled color.
    if (use_gradient_remap) {
        float luma = dot(base.rgb, vec3(0.299, 0.587, 0.114));
        // If the source pixel is black, force alpha to 0 regardless of gradient
        if (luma < black_threshold) {
            base.a = 0.0;
        }
        vec3 grad_rgb = texture(gradient_tex, vec2(luma, 0.5)).rgb;
        // If gradient is effectively unassigned (default white), keep base color
        if (grad_rgb != vec3(1.0)) {
            base.rgb = grad_rgb;
        }
    }
    int steps = int(clamp(glow_radius, 0.0, 64.0));
    int rays = 24;
    vec2 px = SCREEN_PIXEL_SIZE;
    float min_dist = float(steps) + 1.0;
    bool found = false;

    // DISSOLVE
    float noise = get_noise(uv);
    float dissolve_cut = dissolve_progress;
    bool is_cut = (base.a > 0.1) && (noise < dissolve_cut);

    // SPRITE / OUTLINE
    // We compute an outline (glow) from neighboring alpha samples below and
    // then composite it behind the sprite color so semi-transparent pixels
    // reveal the outline underneath.
    if (steps > 0) {
        for (int d = 0; d < rays; d++) {
            float angle = 6.283185 * float(d) / float(rays); // 2*PI
            vec2 dir = vec2(cos(angle), sin(angle));
            for (int i = 1; i <= steps; i++) {
                vec2 offset = dir * px * float(i);
                vec2 sample_uv = deform_uv(UV + offset);

                vec4 sample = texture(TEXTURE, sample_uv);
                float sample_noise = get_noise(sample_uv);
                bool sample_cut = (sample.a > 0.1) && (sample_noise < dissolve_cut);
                if (sample.a > 0.1 && !sample_cut) {
                    min_dist = min(min_dist, float(i));
                    found = true;
                    break;
                }
            }
        }
        vec4 outline_col = vec4(0.0);
        if (found && min_dist <= float(steps)) {
            // Single continuous gradient from inner edge (color 1) to outer edge (color 2).
            float denom = max(float(steps - 1), 1.0);
            float t = clamp((min_dist - 1.0) / denom, 0.0, 1.0);
            outline_col = mix(outline_color_inner, outline_color_outer, t);
            // Fade only the outermost 10% of the outline to transparent.
            float edge_fade = 1.0 - smoothstep(0.9, 1.0, t);
            outline_col.a *= edge_fade;
        }

        // If the sprite pixel exists (not cut) and has some alpha, composite the
        // outline behind the sprite color using the sprite alpha as the mix factor.
        if (base.a > 0.0 && !is_cut) {
            if (outline_col.a > 0.0) {
                // mix outline behind sprite: when sprite is fully opaque it covers outline,
                // when semi-transparent the outline shows through proportionally
                COLOR = mix(outline_col, base * modulate_color, base.a);
            } else {
                COLOR = base * modulate_color;
            }
        } else {
            // no sprite pixel here: show outline alone (if any)
            COLOR = outline_col;
        }
    } else {
        COLOR = vec4(0.0);
    }
}
