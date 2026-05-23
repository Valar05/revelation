shader_type canvas_item;

uniform float progress : hint_range(0.0, 1.0) = 0.0;
uniform float pulse_amount : hint_range(0.0, 4.0) = 0.0;
uniform vec2 pulse_center = vec2(0.5, 0.5);
uniform float max_radius : hint_range(0.0, 1.5) = 0.7;
uniform float ring_width : hint_range(0.001, 0.75) = 0.12;
uniform float front_edge_width : hint_range(0.001, 0.2) = 0.02;
uniform float stretch_strength : hint_range(0.0, 1.0) = 0.04;
uniform float band_curve : hint_range(0.2, 4.0) = 1.0;
uniform float pinch_width : hint_range(0.0, 0.75) = 0.16;
uniform float pinch_curve : hint_range(0.2, 4.0) = 1.5;
uniform float compensation_strength : hint_range(0.0, 1.5) = 0.45;


float wave_profile(float signed_distance, float trail_width, float front_width) {
	if (signed_distance >= 0.0) {
		if (signed_distance >= front_width) {
			return 0.0;
		}

		float front_t = 1.0 - smoothstep(0.0, front_width, signed_distance);
		return pow(front_t, band_curve);
	}

	float trail_distance = -signed_distance;
	if (trail_distance >= trail_width) {
		return 0.0;
	}

	float trail_t = 1.0 - smoothstep(0.0, trail_width, trail_distance);
	return pow(trail_t, band_curve);
}


float front_compensation_profile(float signed_distance, float pinch_size) {
	if (pinch_size <= 0.0001 || signed_distance <= 0.0 || signed_distance >= pinch_size) {
		return 0.0;
	}

	float pinch_t = smoothstep(0.0, 1.0, signed_distance / pinch_size);
	return pow(1.0 - pinch_t, pinch_curve);
}

void fragment() {
	vec4 base_color = COLOR;
	float amount = pulse_amount * stretch_strength;
	vec2 sample_uv = UV;

	if (amount > 0.00001) {
		vec2 texture_size = 1.0 / TEXTURE_PIXEL_SIZE;
		vec2 aspect = texture_size / max(texture_size.x, texture_size.y);
		vec2 centered_uv = (UV - pulse_center) * aspect;
		float radial_distance = length(centered_uv);
		vec2 direction = radial_distance > 0.00001 ? centered_uv / radial_distance : vec2(1.0, 0.0);

		float radius = max_radius * progress;
		float signed_distance = radial_distance - radius;
		float trail_width = max(ring_width, 0.0001);
		float front_width = max(front_edge_width, 0.0001);
		float pinch_profile = wave_profile(signed_distance, trail_width, front_width);
		float stretch_profile = front_compensation_profile(signed_distance, pinch_width);
		float radial_scale = 1.0 + amount * pinch_profile - amount * compensation_strength * stretch_profile;
		float sample_signed_distance = signed_distance * radial_scale;
		float sample_distance = max(radius + sample_signed_distance, 0.0);
		sample_uv = pulse_center + (direction * sample_distance) / aspect;
	}

	vec4 original_texel = texture(TEXTURE, UV);
	vec4 sampled_color = texture(TEXTURE, clamp(sample_uv, vec2(0.0), vec2(1.0)));
	float safe_alpha = max(original_texel.a, 0.00001);
	vec3 safe_rgb = max(original_texel.rgb, vec3(0.00001));
	vec4 modulation = vec4(1.0);
	modulation.rgb = base_color.rgb / safe_rgb;
	modulation.a = base_color.a / safe_alpha;
	COLOR = sampled_color * modulation;
}
