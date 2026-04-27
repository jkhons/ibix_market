import { create } from 'zustand';
import notificationService, { Notification } from '@/services/notificationService';

interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
  isLoading: boolean;

  fetchNotifications: (page?: number) => Promise<void>;
  fetchUnreadCount: () => Promise<void>;
  markAsRead: (ids: number[]) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  addNotification: (notification: Notification) => void;
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],
  unreadCount: 0,
  isLoading: false,

  fetchNotifications: async (page = 1) => {
    set({ isLoading: true });
    try {
      const data = await notificationService.getNotifications({ page, page_size: 20 });
      if (page === 1) {
        set({ notifications: data.items, unreadCount: data.nao_lidas });
      } else {
        set((state) => ({
          notifications: [...state.notifications, ...data.items],
          unreadCount: data.nao_lidas,
        }));
      }
    } finally {
      set({ isLoading: false });
    }
  },

  fetchUnreadCount: async () => {
    try {
      const data = await notificationService.getUnreadCount();
      set({ unreadCount: data.nao_lidas });
    } catch {
      // silently fail
    }
  },

  markAsRead: async (ids) => {
    await notificationService.markAsRead(ids);
    set((state) => ({
      notifications: state.notifications.map((n) =>
        ids.includes(n.id) ? { ...n, lida: true } : n,
      ),
      unreadCount: Math.max(0, state.unreadCount - ids.length),
    }));
  },

  markAllAsRead: async () => {
    const unread = get().notifications.filter((n) => !n.lida).map((n) => n.id);
    if (unread.length > 0) {
      await notificationService.markAsRead(unread);
      set((state) => ({
        notifications: state.notifications.map((n) => ({ ...n, lida: true })),
        unreadCount: 0,
      }));
    }
  },

  addNotification: (notification) => {
    set((state) => ({
      notifications: [notification, ...state.notifications],
      unreadCount: state.unreadCount + (notification.lida ? 0 : 1),
    }));
  },
}));
