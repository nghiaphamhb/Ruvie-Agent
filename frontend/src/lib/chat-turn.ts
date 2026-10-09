import type { UiMessage } from './i18n/messages.ts';
import type { Citation } from './chat-api';

export type ChatTurn = {
  id: number;
  question: string;
  answer: string;
  citations: Citation[];
  status: 'loading' | 'streaming' | 'completed' | 'error';
  error: UiMessage | null;
};
