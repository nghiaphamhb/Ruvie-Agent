import type { UiMessage } from '../../i18n/messages.ts';
import type { Citation } from './chat-api.ts';

export type ChatTurn = {
  id: number;
  question: string;
  modelId?: string;
  answer: string;
  citations: Citation[];
  status: 'loading' | 'streaming' | 'completed' | 'error' | 'stopped';
  error: UiMessage | null;
};
