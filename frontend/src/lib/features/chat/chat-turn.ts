import type { UiMessage } from '../../i18n/messages.ts';
import type { Citation } from './chat-api.ts';

export type ChatTurn = {
  id: number;
  serverId?: string;
  createdAt?: string;
  attemptId?: string;
  requestId?: string;
  contentUnavailable?: boolean;
  question: string;
  modelId?: string;
  answer: string;
  citations: Citation[];
  status: 'loading' | 'streaming' | 'completed' | 'error' | 'stopped' | 'interrupted';
  error: UiMessage | null;
};
