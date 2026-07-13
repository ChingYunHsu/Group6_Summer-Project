import {
    Modal,
    ScrollView,
    StyleSheet,
    Text,
    TouchableOpacity,
    View,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";

import RouteStep from "./RouteStep";

interface Props {
  visible: boolean;
  destinationName: string;
  durationMinutes: number;
  steps: string[];
  onStartNavigation: () => void;
  onClose: () => void;
}

export default function RouteDetailModal({
  visible,
  destinationName,
  durationMinutes,
  steps,
  onStartNavigation,
  onClose,
}: Props) {
  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
    >
      <View style={styles.overlay}>

        <View style={styles.sheet}>

          <View style={styles.handle} />

          <View style={styles.header}>

            <View style={{ flex: 1 }}>

              <Text style={styles.title}>
                Route Details
              </Text>

              <Text style={styles.subtitle}>
                {destinationName}
              </Text>

            </View>

            <TouchableOpacity
              onPress={onClose}
            >
              <Ionicons
                name="close"
                size={24}
                color={Colours.text}
              />
            </TouchableOpacity>

          </View>

          <View style={styles.summaryCard}>

            <Ionicons
              name="navigate"
              size={22}
              color={Colours.primary}
            />

            <View style={{ marginLeft: 12 }}>

              <Text style={styles.summaryTitle}>
                Estimated Journey
              </Text>

              <Text style={styles.summaryValue}>
                {durationMinutes} minutes
              </Text>

            </View>

          </View>

          <Text style={styles.sectionTitle}>
            Navigation Steps
          </Text>

          <ScrollView
            style={styles.stepsContainer}
            showsVerticalScrollIndicator={false}
          >

            {steps.map((step, index) => (

              <RouteStep
                key={index}
                stepNumber={index + 1}
                title={step}
              />

            ))}

          </ScrollView>

          <TouchableOpacity
            style={styles.startButton}
            onPress={onStartNavigation}
          >

            <Ionicons
              name="navigate"
              size={20}
              color="#FFFFFF"
            />

            <Text style={styles.startButtonText}>
              Start Navigation
            </Text>

          </TouchableOpacity>

        </View>

      </View>

    </Modal>
  );
}

const styles = StyleSheet.create({

  overlay: {
    flex: 1,
    justifyContent: "flex-end",
    backgroundColor: "rgba(0,0,0,0.25)",
  },

  sheet: {
    backgroundColor: "#FFFFFF",
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    padding: 24,
    maxHeight: "90%",
  },

  handle: {
    alignSelf: "center",
    width: 48,
    height: 5,
    borderRadius: 3,
    backgroundColor: "#D1D5DB",
    marginBottom: 20,
  },

  header: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 20,
  },

  title: {
    ...Typography.h2,
  },

  subtitle: {
    marginTop: 4,
    color: Colours.muted,
    fontSize: 15,
  },

  summaryCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#EFF6FF",
    borderRadius: 16,
    padding: 16,
    marginBottom: 20,
  },

  summaryTitle: {
    fontSize: 13,
    color: Colours.muted,
  },

  summaryValue: {
    fontSize: 22,
    fontWeight: "700",
    color: Colours.primary,
    marginTop: 2,
  },

  sectionTitle: {
    fontWeight: "700",
    fontSize: 16,
    marginBottom: 12,
  },

  stepsContainer: {
    maxHeight: 420,
    marginBottom: 20,
  },

  startButton: {
    backgroundColor: Colours.primary,
    borderRadius: 18,
    paddingVertical: 18,
    justifyContent: "center",
    alignItems: "center",
    flexDirection: "row",
  },

  startButtonText: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 17,
    marginLeft: 10,
  },

});