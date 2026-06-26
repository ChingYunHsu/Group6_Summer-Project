
import {
    StyleSheet,
    TextInput,
    TouchableOpacity,
    View,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import { Colours } from "../constants/colours";

interface Props {

  value: string;

  onChangeText: (text: string) => void;

  onFilterPress: () => void;

}

export default function MapSearchBar({

  value,

  onChangeText,

  onFilterPress,

}: Props) {

  return (

    <View style={styles.container}>

      <Ionicons
        name="search"
        size={20}
        color={Colours.muted}
      />

      <TextInput

        value={value}

        onChangeText={onChangeText}

        placeholder="Search clinics or pharmacies..."

        placeholderTextColor={Colours.muted}

        autoCorrect={false}

        autoCapitalize="none"

        style={styles.input}

        returnKeyType="search"

      />

      <TouchableOpacity
        onPress={onFilterPress}
      >

        <Ionicons

          name="options"

          size={22}

          color={Colours.primary}

        />

      </TouchableOpacity>

    </View>

  );

}

const styles = StyleSheet.create({

  container: {

    flexDirection: "row",

    alignItems: "center",

    backgroundColor: "#FFFFFF",

    borderRadius: 18,

    paddingHorizontal: 16,

    height: 56,

    shadowColor: "#000",

    shadowOpacity: 0.12,

    shadowRadius: 10,

    shadowOffset: {

      width: 0,

      height: 3,

    },

    elevation: 6,

  },

  input: {

    flex: 1,

    marginLeft: 12,

    color: Colours.text,

    fontSize: 16,

  },

});