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

  it('recalculates unreadCount correctly after remove', () => {
    useNotificationStore.getState().addNotification({ type: 'info', title: 'A', message: '' });
    useNotificationStore.getState().addNotification({ type: 'info', title: 'B', message: '' });
    const id = useNotificationStore.getState().notifications[0].id;
    useNotificationStore.getState().markRead(id);
    // one read, one unread — remove the unread one
    const unreadId = useNotificationStore.getState().notifications.find((n) => !n.read)!.id;
    useNotificationStore.getState().removeNotification(unreadId);
    expect(useNotificationStore.getState().unreadCount).toBe(0);
  });

  it('caps notifications at 100', () => {
    for (let i = 0; i < 110; i++) {
      useNotificationStore.getState().addNotification({ type: 'info', title: `N${i}`, message: '' });
    }
    expect(useNotificationStore.getState().notifications).toHaveLength(100);
  });

  it('new notifications appear at the front of the list', () => {
    useNotificationStore.getState().addNotification({ type: 'info', title: 'First', message: '' });
    useNotificationStore.getState().addNotification({ type: 'info', title: 'Second', message: '' });
    expect(useNotificationStore.getState().notifications[0].title).toBe('Second');
  });

  it('togglePanel flips panelOpen', () => {
    expect(useNotificationStore.getState().panelOpen).toBe(false);
    useNotificationStore.getState().togglePanel();
    expect(useNotificationStore.getState().panelOpen).toBe(true);
    useNotificationStore.getState().togglePanel();
    expect(useNotificationStore.getState().panelOpen).toBe(false);
  });

  it('setPanelOpen sets panelOpen directly', () => {
    useNotificationStore.getState().setPanelOpen(true);
    expect(useNotificationStore.getState().panelOpen).toBe(true);
    useNotificationStore.getState().setPanelOpen(false);
    expect(useNotificationStore.getState().panelOpen).toBe(false);
  });

  it('stores optional actionUrl and data fields', () => {
    useNotificationStore.getState().addNotification({
      type: 'approval',
      title: 'Action needed',
      message: 'Review this',
      actionUrl: '/approvals/1',
      data: { orderId: 42 },
    });
    const n = useNotificationStore.getState().notifications[0];
    expect(n.actionUrl).toBe('/approvals/1');
    expect(n.data).toEqual({ orderId: 42 });
  });

  it('generates a unique id for each notification', () => {
    useNotificationStore.getState().addNotification({ type: 'info', title: 'A', message: '' });
    useNotificationStore.getState().addNotification({ type: 'info', title: 'B', message: '' });
    const [a, b] = useNotificationStore.getState().notifications;
    expect(a.id).not.toBe(b.id);
  });
});
