import {
    KeyboardTypeOptions,
    StyleSheet,
    Text,
    TextInput,
    View,
} from "react-native";

import { Colours } from "../constants/colours";

interface FormInputProps {
  label: string;
  value: string;
  onChangeText: (text: string) => void;
  multiline?: boolean;
  keyboardType?: KeyboardTypeOptions;
}

export default function FormInput({
  label,
  value,
  onChangeText,
  multiline = false,
  keyboardType = "default",
}: FormInputProps) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>
        {label}
      </Text>

      <TextInput
        style={[
          styles.input,
          multiline && styles.multilineInput,
        ]}
        value={value}
        onChangeText={onChangeText}
        multiline={multiline}
        keyboardType={keyboardType}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  field: {
    marginBottom: 18,
  },

  label: {
    color: Colours.muted,
    marginBottom: 8,
    fontSize: 12,
    fontWeight: "600",
  },

  input: {
    minHeight: 56,
    borderWidth: 1,
    borderColor: Colours.border,
    borderRadius: 14,
    paddingHorizontal: 16,
    backgroundColor: Colours.surface,
    color: Colours.text,
  },

  multilineInput: {
    minHeight: 100,
    paddingTop: 14,
    textAlignVertical: "top",
  },
});