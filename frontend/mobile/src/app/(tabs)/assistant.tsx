import { Ionicons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { router } from "expo-router";
import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
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

import { Colours } from "../../constants/colours";
import { Typography } from "../../constants/typography";
import { featuredLanguages } from "../../data/languages";
import { getVenue, sendChatbotMessage } from "../../services/api";
import { Venue } from "../../types/venue";

//
// NOT real yet, because there's nothing on the backend to connect to:
//   - Streaming: /chatbot returns one complete JSON response, not SSE or
//     chunked. A typing indicator stands in for a token-by-token stream.
//   - The AI itself: ask_chatbot() on the backend is presently a static
//     mock — same canned message regardless of what's asked. This UI will
//     work correctly against a real model once the backend calls one; it
//     just can't demonstrate "grounded" answers until then.
//   - Voice input: expo-speech (used elsewhere in this app) is
//     text-to-speech, not speech-to-text — there's no transcription
//     library in this project at all yet. The mic button below shows an
//     honest "not available yet" message rather than doing nothing.

type Citation = { type: string; id: string };

type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  isTyping?: boolean;
  isError?: boolean;
  citations?: Citation[];
  suggestedPrompts?: string[];
};

function parseCitation(raw: string): Citation {
  const separatorIndex = raw.indexOf(":");

  if (separatorIndex === -1) {
    return { type: "source", id: raw };
  }

  return {
    type: raw.slice(0, separatorIndex),
    id: raw.slice(separatorIndex + 1),
  };
}

function ClinicRecommendationCard({ venue }: { venue: Venue }) {
  return (
    <View style={styles.clinicCard}>
      <Ionicons name="medical" size={18} color={Colours.primary} />

      <View style={styles.clinicCardBody}>
        <Text style={styles.clinicCardTitle}>{venue.name}</Text>

        <Text style={styles.clinicCardSubtitle}>
          {venue.open_now ? "Open now" : "Currently closed"}
          {venue.busyness?.busyness_status
            ? ` · ${venue.busyness.busyness_status}`
            : ""}
        </Text>
      </View>
    </View>
  );
}

function CitationChip({ citation }: { citation: Citation }) {
  return (
    <View style={styles.citationChip}>
      <Text style={styles.citationChipText}>
        {citation.type}:{citation.id}
      </Text>
    </View>
  );
}

export default function AssistantScreen() {
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);

  const [currentLanguage, setCurrentLanguage] = useState(
    featuredLanguages.find((l) => l.code === "en") ?? featuredLanguages[0],
  );

  // Resolved venue lookups for "venue:" citations, keyed by venue_id.
  // undefined = not yet requested, null = fetch failed, Venue = resolved.
  const [venueCache, setVenueCache] = useState<Record<string, Venue | null>>(
    {},
  );

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      text: "Hello! I'm your ClearPath Assistant. How can I help you today?",
    },
    {
      id: "2",
      role: "assistant",
      text: "I can help find clinics, explain services, and answer healthcare navigation questions.",
    },
  ]);

  useEffect(() => {
    (async () => {
      const code = await AsyncStorage.getItem("language");
      const match = featuredLanguages.find((l) => l.code === code);
      if (match) setCurrentLanguage(match);
    })();
  }, []);

  // Best-effort venue resolution for any citation of type "venue" that
  // isn't already in the cache. Runs whenever new messages arrive.
  useEffect(() => {
    const venueIds = Array.from(
      new Set(
        messages
          .flatMap((m) => m.citations ?? [])
          .filter((c) => c.type === "venue")
          .map((c) => c.id),
      ),
    );

    const missing = venueIds.filter((id) => !(id in venueCache));

    missing.forEach((id) => {
      getVenue(id)
        .then((venue) => {
          setVenueCache((prev) => ({ ...prev, [id]: venue }));
        })
        .catch((error) => {
          console.error(`Failed to resolve citation venue:${id}`, error);
          setVenueCache((prev) => ({ ...prev, [id]: null }));
        });
    });
  }, [messages, venueCache]);

  const handleSend = async (overrideText?: string) => {
    const text = (overrideText ?? message).trim();
    if (!text || sending) return;

    const userMessageId = `${Date.now()}-user`;
    const typingId = `${Date.now()}-typing`;

    setMessages((prev) => [
      ...prev,
      { id: userMessageId, role: "user", text },
      { id: typingId, role: "assistant", text: "", isTyping: true },
    ]);

    setMessage("");
    setSending(true);

    try {
      const response = await sendChatbotMessage({
        message: text,
        language: currentLanguage.code,
      });

      setMessages((prev) =>
        prev.map((m) =>
          m.id === typingId
            ? {
                id: typingId,
                role: "assistant",
                text: response.message,
                citations: response.citations.map(parseCitation),
                suggestedPrompts: response.suggested_prompts,
              }
            : m,
        ),
      );
    } catch (error) {
      console.error("Chatbot request failed", error);

      setMessages((prev) =>
        prev.map((m) =>
          m.id === typingId
            ? {
                id: typingId,
                role: "assistant",
                text: "Sorry, I couldn't get a response. Please try again.",
                isError: true,
              }
            : m,
        ),
      );
    } finally {
      setSending(false);
    }
  };

  const handleMicPress = () => {
    Alert.alert(
      "Voice input isn't available yet",
      "Type your question for now — voice input needs a speech-to-text library this project doesn't have yet.",
    );
  };

  const renderMessage = ({ item }: { item: Message }) => (
    <View
      style={[
        styles.messageBubble,
        item.role === "user" ? styles.userBubble : styles.assistantBubble,
      ]}
    >
      {item.isTyping ? (
        <ActivityIndicator size="small" color={Colours.primary} />
      ) : (
        <Text
          style={[
            styles.messageText,
            item.role === "user" && styles.userMessageText,
            item.isError && styles.errorMessageText,
          ]}
        >
          {item.text}
        </Text>
      )}

      {!item.isTyping && item.citations && item.citations.length > 0 && (
        <View style={styles.citationsRow}>
          {item.citations.map((citation) => {
            if (citation.type === "venue") {
              const venue = venueCache[citation.id];
              if (venue) {
                return (
                  <ClinicRecommendationCard
                    key={`${citation.type}:${citation.id}`}
                    venue={venue}
                  />
                );
              }
            }

            return (
              <CitationChip
                key={`${citation.type}:${citation.id}`}
                citation={citation}
              />
            );
          })}
        </View>
      )}

      {!item.isTyping &&
        item.suggestedPrompts &&
        item.suggestedPrompts.length > 0 && (
          <View style={styles.promptsRow}>
            {item.suggestedPrompts.map((prompt) => (
              <TouchableOpacity
                key={prompt}
                style={styles.promptChip}
                onPress={() => handleSend(prompt)}
                disabled={sending}
              >
                <Text style={styles.promptChipText}>{prompt}</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        {/* Header */}

        <View style={styles.header}>
          <View>
            <Text style={styles.title}>Assistant</Text>

            <Text style={styles.subtitle}>
              Responding in {currentLanguage.english}
            </Text>
          </View>

          <TouchableOpacity
            style={styles.languageButton}
            onPress={() =>
              router.push({ pathname: "/language", params: { origin: "app" } })
            }
          >
            <Ionicons name="language" size={20} color={Colours.primary} />
          </TouchableOpacity>
        </View>

        {/* Chat */}

        <FlatList
          data={messages}
          renderItem={renderMessage}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.chatContent}
          showsVerticalScrollIndicator={false}
        />

        {/* Input */}

        <View style={styles.inputContainer}>
          <TouchableOpacity style={styles.micButton} onPress={handleMicPress}>
            <Ionicons name="mic" size={22} color={Colours.primary} />
          </TouchableOpacity>

          <TextInput
            style={styles.input}
            placeholder="Ask a question..."
            placeholderTextColor={Colours.muted}
            value={message}
            onChangeText={setMessage}
            multiline
          />

          <TouchableOpacity
            style={[styles.sendButton, sending && styles.sendButtonDisabled]}
            onPress={() => handleSend()}
            disabled={sending}
          >
            <Ionicons name="send" size={18} color="#FFFFFF" />
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
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: Colours.border,
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
    backgroundColor: Colours.surfaceLight,
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
    backgroundColor: Colours.surface,
    alignSelf: "flex-start",
    borderWidth: 1,
    borderColor: Colours.border,
  },

  userBubble: {
    backgroundColor: Colours.primary,
    alignSelf: "flex-end",
  },

  messageText: {
    color: Colours.text,
    lineHeight: 20,
  },

  userMessageText: {
    color: "#FFFFFF",
  },

  errorMessageText: {
    color: "#D32F2F",
  },

  citationsRow: {
    marginTop: 12,
    gap: 8,
  },

  citationChip: {
    alignSelf: "flex-start",
    backgroundColor: Colours.surfaceLight,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderWidth: 1,
    borderColor: Colours.border,
  },

  citationChipText: {
    fontSize: 12,
    color: Colours.muted,
  },

  clinicCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colours.surfaceLight,
    borderRadius: 14,
    padding: 12,
    borderWidth: 1,
    borderColor: Colours.border,
  },

  clinicCardBody: {
    marginLeft: 10,
    flex: 1,
  },

  clinicCardTitle: {
    fontWeight: "700",
    color: Colours.text,
  },

  clinicCardSubtitle: {
    fontSize: 12,
    color: Colours.muted,
    marginTop: 2,
  },

  promptsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    marginTop: 12,
    gap: 8,
  },

  promptChip: {
    backgroundColor: Colours.primary,
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 8,
  },

  promptChipText: {
    color: "#FFFFFF",
    fontSize: 13,
    fontWeight: "600",
  },

  inputContainer: {
    flexDirection: "row",
    alignItems: "flex-end",
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: Colours.border,
    backgroundColor: Colours.background,
  },

  micButton: {
    width: 42,
    height: 42,
    borderRadius: 21,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: Colours.surfaceLight,
    borderWidth: 1,
    borderColor: Colours.border,
    marginRight: 10,
  },

  input: {
    flex: 1,
    minHeight: 44,
    maxHeight: 120,
    backgroundColor: Colours.surface,
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
    backgroundColor: Colours.primary,
    justifyContent: "center",
    alignItems: "center",
    marginLeft: 10,
  },

  sendButtonDisabled: {
    opacity: 0.5,
  },
});
