/**
 * MessageThread — shared owner↔clinic conversation for one animal (#22).
 *
 * Used on both sides: the staff AnimalDetailModal ("Messages" tab) and the pet
 * owner's portal. `isOwner` flips the bubble alignment so "my" messages sit on
 * the right. Thread is append-only and stored against the animal for audit.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { Send } from 'lucide-react';
import { apiClient, type Message } from '../../utils/api';
import { useWebSocket } from '../../hooks/useWebSocket';
import Button from '../ui/Button';

interface MessageThreadProps {
  animalId: number;
  /** True when rendered for the pet owner (flips bubble alignment). */
  isOwner?: boolean;
}

const MessageThread: React.FC<MessageThreadProps> = ({ animalId, isOwner = false }) => {
  const { t } = useTranslation('patients');
  const [messages, setMessages] = useState<Message[]>([]);
  const [body, setBody] = useState('');
  const [sending, setSending] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  const load = useCallback(() => {
    apiClient.getMessages(animalId)
      .then((m) => {
        setMessages(m);
        // Mark the other side's messages as read on open (best-effort).
        apiClient.markMessagesRead(animalId).catch(() => {});
      })
      .catch(() => {});
  }, [animalId]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { endRef.current?.scrollIntoView?.({ block: 'end' }); }, [messages]);

  // Live updates: append new messages for this animal as they arrive, deduped
  // by id (our own sent message is echoed back to us). Polling is no longer the
  // only path, but the REST API remains the source of truth.
  const onSocketMessage = useCallback((m: any) => {
    if (m?.type !== 'message_created' || m.animal_patient_id !== animalId || !m.message) return;
    setMessages((prev) => (prev.some((x) => x.id === m.message.id) ? prev : [...prev, m.message]));
    // If it came from the other side, mark the thread read (it's open).
    if (m.message.from_owner !== isOwner) {
      apiClient.markMessagesRead(animalId).catch(() => {});
    }
  }, [animalId, isOwner]);

  useWebSocket('/ws/messages/', { onMessage: onSocketMessage });

  const send = async () => {
    if (!body.trim()) return;
    setSending(true);
    try {
      const msg = await apiClient.sendMessage(animalId, body.trim());
      setMessages((prev) => [...prev, msg]);
      setBody('');
    } catch {
      toast.error(t('messages.sendFailed'));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto space-y-2 mb-3 max-h-80" data-testid="message-list">
        {messages.length === 0 ? (
          <p className="text-sm text-slate-400 text-center py-6">{t('messages.empty')}</p>
        ) : messages.map((m) => {
          const mine = m.from_owner === isOwner;
          return (
            <div key={m.id} className={`flex ${mine ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm ${
                mine
                  ? 'bg-medical-500 text-white rounded-br-sm'
                  : 'bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-100 rounded-bl-sm'
              }`}>
                <p className="whitespace-pre-line break-words">{m.body}</p>
                <p className={`text-[10px] mt-1 ${mine ? 'text-medical-100' : 'text-slate-400'}`}>
                  {new Date(m.created_at).toLocaleString()}
                </p>
              </div>
            </div>
          );
        })}
        <div ref={endRef} />
      </div>

      <div className="flex items-end gap-2">
        <textarea
          className="flex-1 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-medical bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-medical-500 text-sm resize-none h-12"
          placeholder={t('messages.placeholder')}
          value={body}
          aria-label={t('messages.placeholder')}
          onChange={(e) => setBody(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
        />
        <Button variant="medical" leftIcon={Send} onClick={send} disabled={sending || !body.trim()}>
          {t('messages.send')}
        </Button>
      </div>
    </div>
  );
};

export default MessageThread;
