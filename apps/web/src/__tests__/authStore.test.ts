import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from '@/stores/authStore';

const mockUser = {
  id: 'user-1',
  email: 'test@example.com',
  name: 'Test User',
  onboardingComplete: false,
};

describe('authStore', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      token: null,
    });
  });

  describe('login()', () => {
    it('sets user, token, isAuthenticated, and clears isLoading', () => {
      useAuthStore.getState().login(mockUser, 'tok-123');
      const s = useAuthStore.getState();
      expect(s.user).toEqual(mockUser);
      expect(s.token).toBe('tok-123');
      expect(s.isAuthenticated).toBe(true);
      expect(s.isLoading).toBe(false);
    });
  });

  describe('logout()', () => {
    it('clears all auth state', () => {
      useAuthStore.getState().login(mockUser, 'tok-123');
      useAuthStore.getState().logout();
      const s = useAuthStore.getState();
      expect(s.user).toBeNull();
      expect(s.token).toBeNull();
      expect(s.isAuthenticated).toBe(false);
      expect(s.isLoading).toBe(false);
    });
  });

  describe('completeOnboarding()', () => {
    it('sets user.onboardingComplete to true', () => {
      useAuthStore.getState().login(mockUser, 'tok');
      useAuthStore.getState().completeOnboarding();
      expect(useAuthStore.getState().user?.onboardingComplete).toBe(true);
    });

    it('preserves all other user fields', () => {
      useAuthStore.getState().login(mockUser, 'tok');
      useAuthStore.getState().completeOnboarding();
      const user = useAuthStore.getState().user!;
      expect(user.id).toBe(mockUser.id);
      expect(user.email).toBe(mockUser.email);
      expect(user.name).toBe(mockUser.name);
    });

    it('is a no-op when user is null', () => {
      useAuthStore.getState().completeOnboarding();
      expect(useAuthStore.getState().user).toBeNull();
    });
  });

  describe('updateUser()', () => {
    it('merges partial updates into the current user', () => {
      useAuthStore.getState().login(mockUser, 'tok');
      useAuthStore.getState().updateUser({ name: 'New Name', avatar: 'avatar.png' });
      const user = useAuthStore.getState().user!;
      expect(user.name).toBe('New Name');
      expect(user.avatar).toBe('avatar.png');
      expect(user.email).toBe(mockUser.email);
    });

    it('does not replace unmentioned fields', () => {
      useAuthStore.getState().login({ ...mockUser, avatar: 'old.png' }, 'tok');
      useAuthStore.getState().updateUser({ name: 'Updated' });
      expect(useAuthStore.getState().user?.avatar).toBe('old.png');
    });

    it('is a no-op when user is null', () => {
      useAuthStore.getState().updateUser({ name: 'Ghost' });
      expect(useAuthStore.getState().user).toBeNull();
    });
  });

  describe('setLoading()', () => {
    it('sets isLoading to true', () => {
      useAuthStore.getState().setLoading(true);
      expect(useAuthStore.getState().isLoading).toBe(true);
    });

    it('sets isLoading to false', () => {
      useAuthStore.setState({ isLoading: true });
      useAuthStore.getState().setLoading(false);
      expect(useAuthStore.getState().isLoading).toBe(false);
    });
  });
});
