import React from 'react';
import { Tabs } from 'expo-router';
import { View, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '@/hooks/useTheme';
import { Badge } from '@/components/ui';
import { Icon, type IconName } from '@/components/ui/Icon';
import { useCartStore } from '@/store/cartStore';
import { useNotificationStore } from '@/store/notificationStore';

type TabConfig = {
  name: string;
  title: string;
  icon: IconName;
  getBadge?: () => number;
};

const TABS: TabConfig[] = [
  { name: 'index', title: 'Início', icon: 'home' },
  { name: 'categorias', title: 'Categorias', icon: 'grid' },
  { name: 'carrinho', title: 'Carrinho', icon: 'cart', getBadge: () => useCartStore.getState().totalItems() },
  { name: 'pedidos', title: 'Pedidos', icon: 'clipboard' },
  { name: 'perfil', title: 'Perfil', icon: 'user' },
];

function TabBarIcon({ icon, color, badge }: { icon: IconName; color: string; badge?: number }) {
  return (
    <View style={styles.iconContainer}>
      <Icon name={icon} size={22} color={color} />
      {badge !== undefined && badge > 0 && (
        <View style={styles.badgeContainer}>
          <Badge count={badge} variant="error" size="sm" />
        </View>
      )}
    </View>
  );
}

export default function TabLayout() {
  const { colors, shadow } = useTheme();
  const insets = useSafeAreaInsets();
  const cartCount = useCartStore((s) => s.totalItems());
  const unreadNotif = useNotificationStore((s) => s.unreadCount);

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.tabBarActive,
        tabBarInactiveTintColor: colors.tabBarInactive,
        tabBarStyle: {
          backgroundColor: colors.tabBarBackground,
          borderTopColor: colors.borderLight,
          borderTopWidth: StyleSheet.hairlineWidth,
          height: 60 + insets.bottom,
          paddingTop: 6,
          paddingBottom: insets.bottom + 4,
          ...shadow('sm'),
        },
        tabBarLabelStyle: {
          fontSize: 11,
          marginTop: 2,
        },
      }}
    >
      {TABS.map((tab) => {
        let badge: number | undefined;
        if (tab.name === 'carrinho') badge = cartCount;
        if (tab.name === 'perfil') badge = unreadNotif;

        return (
          <Tabs.Screen
            key={tab.name}
            name={tab.name}
            options={{
              title: tab.title,
              tabBarIcon: ({ color }) => (
                <TabBarIcon icon={tab.icon} color={color} badge={badge} />
              ),
            }}
          />
        );
      })}
    </Tabs>
  );
}

const styles = StyleSheet.create({
  iconContainer: {
    width: 28,
    height: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeContainer: {
    position: 'absolute',
    top: -6,
    right: -10,
  },
});
