#!/usr/bin/env python3
import rospy
import csv
import numpy as np
from geometry_msgs.msg import PoseStamped, WrenchStamped
from franka_msgs.msg import FrankaState
from datetime import datetime

class FrankaLogger:
    def __init__(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.file = open(f'franka_log_{timestamp}.csv', 'w')
        self.writer = csv.writer(self.file)
        self.writer.writerow([
            'time', 'x', 'y', 'z', 'x_d', 'y_d', 'z_d',
            'vx', 'vy', 'vz', 'fx', 'fy', 'fz',
            'error', 'power', 'cumulative_energy'
        ])

        self.pose = None
        self.desired = None
        self.force = None
        self.prev_time = rospy.Time.now()
        self.prev_pos = None
        self.energy = 0.0

        rospy.Subscriber("/franka_state_controller/franka_states", FrankaState, self.cb_franka_state)
        rospy.Subscriber("/passiveDS/desired_pose", PoseStamped, self.cb_desired)
        rospy.Subscriber("/franka_state_controller/F_ext", WrenchStamped, self.cb_force)

        print("Logger initialized. Waiting for messages...")

    def cb_franka_state(self, msg):
        T = np.array(msg.O_T_EE).reshape((4, 4), order='F')  # 'F' = column-major
        self.pose = np.array([T[0, 3], T[1, 3], T[2, 3]])  # Extract translation
        print(f"[POSE] {self.pose}")



    def cb_desired(self, msg):
        self.desired = np.array([
            msg.pose.position.x,
            msg.pose.position.y,
            msg.pose.position.z
        ])
        print(f"[DESIRED] {self.desired}")

    def cb_force(self, msg):
        self.force = np.array([
            msg.wrench.force.x,
            msg.wrench.force.y,
            msg.wrench.force.z
        ])
        print(f"[FORCE] {self.force}")

    def run(self):
        rate = rospy.Rate(50)
        while not rospy.is_shutdown():
            if self.pose is not None and self.desired is not None and self.force is not None:
                now = rospy.Time.now()
                t = now.to_sec()
                dt = (now - self.prev_time).to_sec()
                self.prev_time = now

                if self.prev_pos is None:
                    vx, vy, vz = 0.0, 0.0, 0.0
                else:
                    dx = self.pose - self.prev_pos
                    vx, vy, vz = dx / dt if dt > 0 else (0.0, 0.0, 0.0)

                self.prev_pos = self.pose.copy()

                error = np.linalg.norm(self.pose - self.desired)

                velocity = np.array([vx, vy, vz])
                power = np.dot(self.force, velocity)
                self.energy += power * dt if dt > 0 else 0.0

                self.writer.writerow([
                    t, *self.pose, *self.desired,
                    vx, vy, vz, *self.force,
                    error, power, self.energy
                ])
                print(f"[LOGGED] t={t:.2f}, err={error:.4f}, P={power:.3f}, E={self.energy:.3f}")
            else:
                print("[WAITING] Missing data from one or more topics.")
            rate.sleep()


if __name__ == '__main__':
    rospy.init_node('franka_logger')
    logger = FrankaLogger()
    logger.run()

