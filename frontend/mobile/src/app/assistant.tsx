import { Ionicons } from "@expo/vector-icons";
import { useState } from "react";
import {
  FlatList,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";

type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
};

export default function AssistantScreen() {
  const [message, setMessage] = useState("");

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      text:
        "Hello! I'm your ClearPath Assistant. How can I help you today?",
    },
    {
      id: "2",
      role: "assistant",
      text:
        "I can help find clinics, explain services, and answer healthcare navigation questions.",
    },
  ]);

  const handleSend = () => {
    if (!message.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      text: message.trim(),
    };

    const assistantReply: Message = {
      id: `${Date.now()}-reply`,
      role: "assistant",
      text:
        "Backend chatbot integration coming soon.",
    };

    setMessages((prev) => [
      ...prev,
      userMessage,
      assistantReply,
    ]);

    setMessage("");
  };

  const renderMessage = ({
    item,
  }: {
    item: Message;
  }) => (
    <View
      style={[
        styles.messageBubble,
        item.role === "user"
          ? styles.userBubble
          : styles.assistantBubble,
      ]}
    >
      <Text
        style={[
          styles.messageText,
          item.role === "user" &&
            styles.userMessageText,
        ]}
      >
        {item.text}
      </Text>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        style={styles.container}
        behavior={
          Platform.OS === "ios"
            ? "padding"
            : undefined
        }
      >
        {/* Header */}

        <View style={styles.header}>
          <View>
            <Text style={styles.title}>
              Assistant
            </Text>

            <Text style={styles.subtitle}>
              Responding in English
            </Text>
          </View>

          <TouchableOpacity
            style={styles.languageButton}
          >
            <Ionicons
              name="language"
              size={20}
              color={Colours.primary}
            />
          </TouchableOpacity>
        </View>

        {/* Chat */}

        <FlatList
          data={messages}
          renderItem={renderMessage}
          keyExtractor={(item) => item.id}
          contentContainerStyle={
            styles.chatContent
          }
          showsVerticalScrollIndicator={
            false
          }
        />

        {/* Input */}

        <View style={styles.inputContainer}>
          <TouchableOpacity
            style={styles.micButton}
          >
            <Ionicons
              name="mic"
              size={22}
              color={Colours.primary}
            />
          </TouchableOpacity>

          <TextInput
            style={styles.input}
            placeholder="Ask a question..."
            placeholderTextColor={
              Colours.muted
            }
            value={message}
            onChangeText={setMessage}
            multiline
          />

          <TouchableOpacity
            style={styles.sendButton}
            onPress={handleSend}
          >
            <Ionicons
              name="send"
              size={18}
              color="#FFFFFF"
            />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colours.background,
  },

  header: {
    flexDirection: "row",
    justifyContent:
      "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor:
      Colours.border,
  },

  title: {
    ...Typography.h1,
  },

  subtitle: {
    color: Colours.primary,
    marginTop: 2,
  },

  languageButton: {
    width: 42,
    height: 42,
    borderRadius: 21,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor:
      Colours.surfaceLight,
    borderWidth: 1,
    borderColor: Colours.border,
  },

  chatContent: {
    padding: 20,
  },

  messageBubble: {
    maxWidth: "85%",
    padding: 14,
    borderRadius: 18,
    marginBottom: 12,
  },

  assistantBubble: {
    backgroundColor:
      Colours.surface,
    alignSelf: "flex-start",
    borderWidth: 1,
    borderColor: Colours.border,
  },

  userBubble: {
    backgroundColor:
      Colours.primary,
    alignSelf: "flex-end",
  },

  messageText: {
    color: Colours.text,
    lineHeight: 20,
  },

  userMessageText: {
    color: "#FFFFFF",
  },

  inputContainer: {
    flexDirection: "row",
    alignItems: "flex-end",
    padding: 16,
    borderTopWidth: 1,
    borderTopColor:
      Colours.border,
    backgroundColor:
      Colours.background,
  },

  micButton: {
    width: 42,
    height: 42,
    borderRadius: 21,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor:
      Colours.surfaceLight,
    borderWidth: 1,
    borderColor: Colours.border,
    marginRight: 10,
  },

  input: {
    flex: 1,
    minHeight: 44,
    maxHeight: 120,
    backgroundColor:
      Colours.surface,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: Colours.border,
    paddingHorizontal: 16,
    paddingVertical: 10,
    color: Colours.text,
  },

  sendButton: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor:
      Colours.primary,
    justifyContent: "center",
    alignItems: "center",
    marginLeft: 10,
  },
});