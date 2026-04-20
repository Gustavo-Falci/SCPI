import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Dimensions
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter, usePathname } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Colors } from '../../constants/theme';

const { width } = Dimensions.get('window');

interface MenuItem {
  icon: keyof typeof Ionicons.glyphMap;
  activeIcon: keyof typeof Ionicons.glyphMap;
  route: string;
  label: string;
}

interface FloatingMenuProps {
  items: MenuItem[];
}

export const FloatingMenu = ({ items }: FloatingMenuProps) => {
  const router = useRouter();
  const pathname = usePathname();
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.container, { bottom: Math.max(insets.bottom, 20) }]}>
      <View style={styles.menu}>
        {items.map((item, index) => {
          const isActive = pathname === item.route;
          const color = isActive ? Colors.brand.primary : Colors.brand.textSecondary;
          return (
            <TouchableOpacity
              key={index}
              style={styles.menuItem}
              activeOpacity={0.7}
              accessibilityRole="button"
              accessibilityLabel={item.label}
              accessibilityState={{ selected: isActive }}
              onPress={() => router.push(item.route as any)}
            >
              <Ionicons
                name={isActive ? item.activeIcon : item.icon}
                size={22}
                color={color}
              />
              <Text
                style={[
                  styles.label,
                  { color, fontWeight: isActive ? '700' : '600' }
                ]}
                numberOfLines={1}
              >
                {item.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    left: 0,
    right: 0,
    alignItems: 'center',
    zIndex: 100,
  },
  menu: {
    width: width * 0.9,
    height: 72,
    backgroundColor: Colors.brand.card,
    borderRadius: 32,
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    elevation: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 5 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.05)',
    paddingHorizontal: 8,
  },
  menuItem: {
    minWidth: 56,
    height: 56,
    paddingHorizontal: 4,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 4,
  },
  label: {
    fontSize: 11,
    letterSpacing: 0.2,
  },
});
