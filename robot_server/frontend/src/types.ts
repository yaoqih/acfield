export interface RobotConfig {
  id: string; name: string; tag_id: number; color: string; tag_size: number;
  length: number; width: number; tag_offset_x: number; tag_offset_y: number;
  heading_offset: number; max_v: number; max_omega: number;
  body_offset_x: number; body_offset_y: number;
}
export interface Settings { arena_width: number; arena_height: number; robots: RobotConfig[] }
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
  command_status: string; reason: string; fault: string | null;
  corners: number[][]; trail: number[][];
}
export interface Snapshot {
  mode: 'demo' | 'hardware'; session: string; estop: boolean; timestamp: number;
  system_fault: string | null;
  arena: {width: number; height: number}; robots: Robot[];
  camera: {connected: boolean; fps: number; reason: string};
  events: {time: number; message: string}[];
}
