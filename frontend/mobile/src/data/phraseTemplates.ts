export type SupportedLanguage =
  | "English"
  | "Chinese"
  | "Spanish"
  | "French"
  | "Italian"
  | "German";

export type Scenario =
  | "allergies"
  | "respiratory"
  | "pain"
  | "injury"
  | "cardiac"
  | "general"
  | "emergency"
  | "hospital"
  | "pharmacy";

export interface Phrase {
  english: string;

  translations: {
    Chinese: string;
    Spanish: string;
    French: string;
    Italian: string;
    German: string;
  };
}

export const phraseTemplates: Record<
  Scenario,
  Phrase[]
> = {
  allergies: [
    {
      english: "I am having an allergic reaction.",
      translations: {
        Chinese: "我正在发生过敏反应。",
        Spanish: "Estoy teniendo una reacción alérgica.",
        French: "Je fais une réaction allergique.",
        Italian: "Ho una reazione allergica.",
        German: "Ich habe eine allergische Reaktion.",
      },
    },
    {
      english: "I am allergic to peanuts.",
      translations: {
        Chinese: "我对花生过敏。",
        Spanish: "Soy alérgico al cacahuete.",
        French: "Je suis allergique aux arachides.",
        Italian: "Sono allergico alle arachidi.",
        German: "Ich bin allergisch gegen Erdnüsse.",
      },
    },
    {
      english: "I am allergic to penicillin.",
      translations: {
        Chinese: "我对青霉素过敏。",
        Spanish: "Soy alérgico a la penicilina.",
        French: "Je suis allergique à la pénicilline.",
        Italian: "Sono allergico alla penicillina.",
        German: "Ich bin allergisch gegen Penicillin.",
      },
    },
    {
      english: "My throat is swelling up.",
      translations: {
        Chinese: "我的喉咙正在肿胀。",
        Spanish: "Se me está hinchando la garganta.",
        French: "Ma gorge gonfle.",
        Italian: "Mi si sta gonfiando la gola.",
        German: "Mein Hals schwillt an.",
      },
    },
  ],

  respiratory: [
    {
      english: "I am having trouble breathing.",
      translations: {
        Chinese: "我呼吸困难。",
        Spanish: "Tengo dificultad para respirar.",
        French: "J'ai du mal à respirer.",
        Italian: "Ho difficoltà a respirare.",
        German: "Ich habe Atembeschwerden.",
      },
    },
    {
      english: "I have asthma.",
      translations: {
        Chinese: "我患有哮喘。",
        Spanish: "Tengo asma.",
        French: "Je souffre d'asthme.",
        Italian: "Ho l'asma.",
        German: "Ich habe Asthma.",
      },
    },
    {
      english: "I need my inhaler.",
      translations: {
        Chinese: "我需要吸入器。",
        Spanish: "Necesito mi inhalador.",
        French: "J'ai besoin de mon inhalateur.",
        Italian: "Ho bisogno del mio inalatore.",
        German: "Ich brauche meinen Inhalator.",
      },
    },
    {
      english: "I cannot catch my breath.",
      translations: {
        Chinese: "我喘不过气来。",
        Spanish: "No puedo recuperar el aliento.",
        French: "Je n'arrive pas à reprendre mon souffle.",
        Italian: "Non riesco a riprendere fiato.",
        German: "Ich bekomme keine Luft.",
      },
    },
  ],

  pain: [
    {
      english: "I am in severe pain.",
      translations: {
        Chinese: "我疼得很厉害。",
        Spanish: "Tengo un dolor intenso.",
        French: "J'ai une douleur intense.",
        Italian: "Ho un forte dolore.",
        German: "Ich habe starke Schmerzen.",
      },
    },
    {
      english: "The pain is an 8 out of 10.",
      translations: {
        Chinese: "疼痛程度是8分（满分10分）。",
        Spanish: "El dolor es un 8 de 10.",
        French: "La douleur est de 8 sur 10.",
        Italian: "Il dolore è di 8 su 10.",
        German: "Die Schmerzen sind 8 von 10.",
      },
    },
    {
      english: "It hurts here.",
      translations: {
        Chinese: "这里疼。",
        Spanish: "Me duele aquí.",
        French: "J'ai mal ici.",
        Italian: "Mi fa male qui.",
        German: "Hier tut es weh.",
      },
    },
    {
      english: "The pain is getting worse.",
      translations: {
        Chinese: "疼痛正在加重。",
        Spanish: "El dolor está empeorando.",
        French: "La douleur s'aggrave.",
        Italian: "Il dolore sta peggiorando.",
        German: "Die Schmerzen werden schlimmer.",
      },
    },
  ],

  injury: [
    {
      english: "I think I broke my arm.",
      translations: {
        Chinese: "我觉得我的手臂骨折了。",
        Spanish: "Creo que me rompí el brazo.",
        French: "Je pense m'être cassé le bras.",
        Italian: "Credo di essermi rotto il braccio.",
        German: "Ich glaube, ich habe mir den Arm gebrochen.",
      },
    },
    {
      english: "I am bleeding.",
      translations: {
        Chinese: "我在流血。",
        Spanish: "Estoy sangrando.",
        French: "Je saigne.",
        Italian: "Sto sanguinando.",
        German: "Ich blute.",
      },
    },
    {
      english: "I fell down.",
      translations: {
        Chinese: "我摔倒了。",
        Spanish: "Me caí.",
        French: "Je suis tombé.",
        Italian: "Sono caduto.",
        German: "Ich bin gestürzt.",
      },
    },
    {
      english: "I injured my leg.",
      translations: {
        Chinese: "我的腿受伤了。",
        Spanish: "Me lesioné la pierna.",
        French: "Je me suis blessé à la jambe.",
        Italian: "Mi sono ferito alla gamba.",
        German: "Ich habe mein Bein verletzt.",
      },
    },
  ],

  cardiac: [
    {
      english: "I have chest pain.",
      translations: {
        Chinese: "我胸口疼。",
        Spanish: "Tengo dolor en el pecho.",
        French: "J'ai mal à la poitrine.",
        Italian: "Ho dolore al petto.",
        German: "Ich habe Brustschmerzen.",
      },
    },
    {
      english: "My heart is racing.",
      translations: {
        Chinese: "我的心跳很快。",
        Spanish: "Mi corazón late muy rápido.",
        French: "Mon cœur bat très vite.",
        Italian: "Il mio cuore batte molto velocemente.",
        German: "Mein Herz rast.",
      },
    },
    {
      english: "I feel dizzy.",
      translations: {
        Chinese: "我感到头晕。",
        Spanish: "Me siento mareado.",
        French: "Je me sens étourdi.",
        Italian: "Mi sento stordito.",
        German: "Mir ist schwindelig.",
      },
    },
    {
      english: "I have high blood pressure.",
      translations: {
        Chinese: "我有高血压。",
        Spanish: "Tengo presión arterial alta.",
        French: "J'ai de l'hypertension.",
        Italian: "Ho la pressione alta.",
        German: "Ich habe hohen Blutdruck.",
      },
    },
  ],

  general: [
    {
      english: "I need medical assistance.",
      translations: {
        Chinese: "我需要医疗帮助。",
        Spanish: "Necesito asistencia médica.",
        French: "J'ai besoin d'une assistance médicale.",
        Italian: "Ho bisogno di assistenza medica.",
        German: "Ich brauche medizinische Hilfe.",
      },
    },
    {
      english: "I do not speak English.",
      translations: {
        Chinese: "我不会说英语。",
        Spanish: "No hablo inglés.",
        French: "Je ne parle pas anglais.",
        Italian: "Non parlo inglese.",
        German: "Ich spreche kein Englisch.",
      },
    },
    {
      english: "Can you call an interpreter?",
      translations: {
        Chinese: "您能叫一位翻译吗？",
        Spanish: "¿Puede llamar a un intérprete?",
        French: "Pouvez-vous appeler un interprète ?",
        Italian: "Può chiamare un interprete?",
        German: "Können Sie einen Dolmetscher rufen?",
      },
    },
  ],

  emergency: [
    {
      english: "Please call an ambulance.",
      translations: {
        Chinese: "请叫救护车。",
        Spanish: "Por favor llame una ambulancia.",
        French: "Veuillez appeler une ambulance.",
        Italian: "Per favore chiami un'ambulanza.",
        German: "Bitte rufen Sie einen Krankenwagen.",
      },
    },
    {
      english: "This is an emergency.",
      translations: {
        Chinese: "这是紧急情况。",
        Spanish: "Esto es una emergencia.",
        French: "C'est une urgence.",
        Italian: "Questa è un'emergenza.",
        German: "Dies ist ein Notfall.",
      },
    },
    {
      english: "I need help immediately.",
      translations: {
        Chinese: "我需要立即帮助。",
        Spanish: "Necesito ayuda inmediatamente.",
        French: "J'ai besoin d'aide immédiatement.",
        Italian: "Ho bisogno di aiuto immediatamente.",
        German: "Ich brauche sofort Hilfe.",
      },
    },
  ],

  hospital: [
    {
      english: "Where is the nearest hospital?",
      translations: {
        Chinese: "最近的医院在哪里？",
        Spanish: "¿Dónde está el hospital más cercano?",
        French: "Où est l'hôpital le plus proche ?",
        Italian: "Dov'è l'ospedale più vicino?",
        German: "Wo ist das nächste Krankenhaus?",
      },
    },
    {
      english: "I need to see a doctor.",
      translations: {
        Chinese: "我需要看医生。",
        Spanish: "Necesito ver a un médico.",
        French: "J'ai besoin de voir un médecin.",
        Italian: "Ho bisogno di vedere un medico.",
        German: "Ich muss einen Arzt aufsuchen.",
      },
    },
    {
      english: "How long is the wait?",
      translations: {
        Chinese: "需要等多久？",
        Spanish: "¿Cuánto tiempo de espera hay?",
        French: "Combien de temps faut-il attendre ?",
        Italian: "Quanto tempo bisogna aspettare?",
        German: "Wie lange ist die Wartezeit?",
      },
    },
  ],

  pharmacy: [
    {
      english: "I need medication.",
      translations: {
        Chinese: "我需要药物。",
        Spanish: "Necesito medicación.",
        French: "J'ai besoin de médicaments.",
        Italian: "Ho bisogno di medicine.",
        German: "Ich brauche Medikamente.",
      },
    },
    {
      english: "Where is the nearest pharmacy?",
      translations: {
        Chinese: "最近的药房在哪里？",
        Spanish: "¿Dónde está la farmacia más cercana?",
        French: "Où est la pharmacie la plus proche ?",
        Italian: "Dov'è la farmacia più vicina?",
        German: "Wo ist die nächste Apotheke?",
      },
    },
    {
      english: "Can I get this prescription filled?",
      translations: {
        Chinese: "我可以配这个处方吗？",
        Spanish: "¿Puedo surtir esta receta?",
        French: "Puis-je faire remplir cette ordonnance ?",
        Italian: "Posso far preparare questa prescrizione?",
        German: "Kann ich dieses Rezept einlösen?",
      },
    },
  ],
};
