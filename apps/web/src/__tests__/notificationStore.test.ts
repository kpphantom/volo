import { describe, it, expect, beforeEach } from 'vitest';
import { useNotificationStore } from '@/stores/notificationStore';

describe('notificationStore', () => {
  beforeEach(() => {
    useNotificationStore.getState().clearAll();
  });

  it('starts empty', () => {
    const state = useNotificationStore.getState();
    expect(state.notifications).toHaveLength(0);
    expect(state.unreadCount).toBe(0);
  });

  it('can add notification', () => {
    useNotificationStore.getState().addNotification({
      type: 'info',
      title: 'Test',
      message: 'Hello',
    });
    const state = useNotificationStore.getState();
    expect(state.notifications).toHaveLength(1);
    expect(state.unreadCount).toBe(1);
    expect(state.notifications[0].title).toBe('Test');
  });

  it('can mark read', () => {
    useNotificationStore.getState().addNotification({
      type: 'info',
      title: 'Read me',
      message: 'msg',
    });
    const id = useNotificationStore.getState().notifications[0].id;
    useNotificationStore.getState().markRead(id);
    expect(useNotificationStore.getState().unreadCount).toBe(0);
  });

  it('can mark all read', () => {
    useNotificationStore.getState().addNotification({ type: 'info', title: 'A', message: '' });
    useNotificationStore.getState().addNotification({ type: 'info', title: 'B', message: '' });
    expect(useNotificationStore.getState().unreadCount).toBe(2);
    useNotificationStore.getState().markAllRead();
    expect(useNotificationStore.getState().unreadCount).toBe(0);
  });

  it('can remove notification', () => {
    useNotificationStore.getState().addNotification({ type: 'error', title: 'Del', message: '' });
    const id = useNotificationStore.getState().notifications[0].id;
    useNotificationStore.getState().removeNotification(id);
    expect(useNotificationStore.getState().notifications).toHaveLength(0);
  });
});
