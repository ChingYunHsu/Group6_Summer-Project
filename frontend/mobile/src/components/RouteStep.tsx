import { StyleSheet, Text, View } from "react-native";

import { Colours } from "../constants/colours";

interface Props {
  stepNumber: number;
  title: string;
}

export default function RouteStep({ stepNumber, title }: Props) {
  return (
    <View style={styles.container}>
      <View style={styles.numberCircle}>
        <Text style={styles.number}>{stepNumber}</Text>
      </View>

      <View style={styles.textContainer}>
        <Text style={styles.title}>{title}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    borderRadius: 18,
    backgroundColor: "#FFFFFF",
    borderWidth: 1,
    borderColor: "#E5E7EB",
    marginBottom: 12,
    padding: 16,
  },

  numberCircle: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: Colours.primary,
    justifyContent: "center",
    alignItems: "center",
    marginRight: 14,
  },

  number: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 15,
  },

  textContainer: {
    flex: 1,
  },

  title: {
    fontSize: 15,
    fontWeight: "600",
    color: Colours.text,
  },
});
