#!/usr/bin/env python3
import rospy
import math
from geometry_msgs.msg import Twist, Wrench, Point, Vector3, PoseStamped
from gazebo_msgs.srv import ApplyBodyWrench
from rosgraph_msgs.msg import Clock

class PoseToTwist:
    def __init__(self):
        rospy.init_node('pose_to_twist_passive_ds')

        # Publishers
        self.twist_pub = rospy.Publisher('/passiveDS/desired_twist', Twist, queue_size=10)
        self.pose_pub = rospy.Publisher('/passiveDS/desired_pose', PoseStamped, queue_size=10)

        # Wait for Gazebo services and clock
        rospy.wait_for_service('/gazebo/apply_body_wrench')
        self.push_service = rospy.ServiceProxy('/gazebo/apply_body_wrench', ApplyBodyWrench)
        rospy.wait_for_message("/clock", Clock)

        # Init state
        self.start_time = rospy.get_time()
        self.last_t = 0.0
        self.last_xyz = [1.0, 0.0, 0.0]
        self.push_applied = False

    def compute_position(self, t):
        """Returns x, y, z pose values at time t."""
        if t < 5.0:
            x = 1.0 + 0.2 * math.sin(0.3 * math.pi * t)
            y = 2.5 * math.sin(0.5 * math.pi * t)
            z = 0.5 + 0.05 * math.sin(0.2 * math.pi * t)
        elif t < 7.0:
            fraction = (t - 5.0)
            x = 0.3 - 0.2 * fraction
            y = 0.1 - 0.1 * fraction
            z = 0.2 - 0.05 * fraction
        elif t < 30.0:
            x = 2.0 + 0.6 * (t - 6.0) / 6.0
            y = 0.0
            z = 0.5
        else:
            x, y, z = self.last_xyz  # hold final pose
        return [x, y, z]

    def publish_twist(self, t):
        dt = t - self.last_t if self.last_t > 0.0 else 1.0 / 50.0
        if dt <= 0.0:
            dt = 1e-4  # avoid zero or negative dt

        current_xyz = self.compute_position(t)

        # Compute velocity
        vx = (current_xyz[0] - self.last_xyz[0]) / dt
        vy = (current_xyz[1] - self.last_xyz[1]) / dt
        vz = (current_xyz[2] - self.last_xyz[2]) / dt

        # Clamp speed
        max_speed = 0.3  # m/s
        speed = math.sqrt(vx**2 + vy**2 + vz**2)
        if speed > max_speed:
            scale = max_speed / speed
            vx *= scale
            vy *= scale
            vz *= scale

        # Debug info
        rospy.loginfo_throttle(0.5, f"Twist vel: vx={vx:.3f}, vy={vy:.3f}, vz={vz:.3f}, |v|={speed:.3f}")

        # Publish twist
        twist = Twist()
        twist.linear.x = vx
        twist.linear.y = vy
        twist.linear.z = vz
        twist.angular.x = 0.0
        twist.angular.y = 0.0
        twist.angular.z = 0.0
        self.twist_pub.publish(twist)

        # Publish pose
        pose_msg = PoseStamped()
        pose_msg.header.stamp = rospy.Time.now()
        pose_msg.header.frame_id = "panda_link0"  # Update if your base frame differs
        pose_msg.pose.position.x = current_xyz[0]
        pose_msg.pose.position.y = current_xyz[1]
        pose_msg.pose.position.z = current_xyz[2]
        pose_msg.pose.orientation.w = 1.0  # No rotation
        pose_msg.pose.orientation.x = 0.0
        pose_msg.pose.orientation.y = 0.0
        pose_msg.pose.orientation.z = 0.0
        self.pose_pub.publish(pose_msg)

        # Update state
        self.last_xyz = current_xyz
        self.last_t = t

    def apply_push(self):
        rospy.loginfo("[INFO] Applying external push!")
        wrench = Wrench()
        wrench.force = Vector3(-20.0, 0.0, 0.0)
        wrench.torque = Vector3(0.0, 0.0, 0.0)

        try:
            self.push_service(
                body_name="panda::panda_link7",
                reference_point=Point(0.0, 0.0, 0.0),
                wrench=wrench,
                start_time=rospy.Time(0),
                duration=rospy.Duration(0.1)
            )
            rospy.loginfo("[INFO] Push complete.")
        except rospy.ServiceException as e:
            rospy.logerr(f"[ERROR] Failed to apply push: {e}")

    def run(self):
        rate = rospy.Rate(50)
        while not rospy.is_shutdown():
            t = rospy.get_time() - self.start_time
            self.publish_twist(t)

            if 7.0 <= t < 7.1 and not self.push_applied:
                self.apply_push()
                self.push_applied = True

            if t > 30.0:
                rospy.loginfo("Test complete.")
                break

            rate.sleep()

if __name__ == '__main__':
    try:
        PoseToTwist().run()
    except rospy.ROSInterruptException:
        pass

