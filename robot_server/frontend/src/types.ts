export interface RobotConfig {
  id: string; name: string; tag_id: number; color: string; tag_size: number; tag_height: number;
  length: number; width: number; tag_offset_x: number; tag_offset_y: number;
  heading_offset: number; max_v: number; max_omega: number;
  body_offset_x: number; body_offset_y: number;
}
export interface Settings { vision_url: string; arena_width: number; arena_height: number; robots: RobotConfig[] }
export interface TagSpec {
  name: string; role: string; size_m: number; height_m: number;
  heading_offset_deg?: number; world_xyz_m?: [number, number, number];
}
export interface VisionProfile {
  source: string; enabled: boolean; width: number; height: number; fps: number;
  family: 'tag36h11'; decimate: number;
  camera: { image_width: number; image_height: number;
    camera_matrix: [[number, number, number], [number, number, number], [number, number, number]];
    dist_coeffs: number[] } | null;
  tags: Record<string, TagSpec>;
  world: { configured: boolean; boundary_xy_m: number[][] };
  saved_world?: boolean;
}
export interface VisionStatus {
  status: string; source?: string; source_kind?: string; width?: number; height?: number;
  fps?: number; frame_age_ms?: number; calibrated?: boolean; world_calibrated?: boolean;
  world_info?: { rms_px: number }; warnings?: string[]; error?: string;
}
export interface VisionResponse { config: VisionProfile; state: VisionStatus }
export interface Robot {
  config: RobotConfig; x: number | null; y: number | null; theta: number | null;
  online: boolean; visible: boolean; armed: boolean; battery: number | null;
  bound: boolean; arm_pending: boolean; control_owner: string | null;
  device_state: string | null; firmware: string | null; voltage_v: number | null;
  effective_max_v: number; effective_max_omega: number;
  wheel_left: number | null; wheel_right: number | null; stop_reason: string | null;
  encoder_left: number | null; encoder_right: number | null;
  pose_age_ms: number | null; heartbeat_age_ms: number | null;
  measured_v: number | null; measured_omega: number | null;
  estimated_v: number | null; acceleration: number | null;
  target_v: number; target_omega: number; seq: number; ack_seq: number;
  command_status: string; reason: string; fault: string | null; warning: string | null;
  clock_synced: boolean; clock_uncertainty_ms: number | null;
  sampled_at_ms: number | null; applied_seq: number | null;
  corners: number[][]; trail: number[][];
}
export interface Snapshot {
  mode: 'demo' | 'hardware'; session: string; estop: boolean; timestamp: number;
  allow_unlocalized_control: boolean;
  system_fault: string | null;
  arena: {width: number; height: number}; robots: Robot[];
  camera: {connected: boolean; available?: boolean; fps: number; reason: string};
  events: {time: number; message: string}[];
}
