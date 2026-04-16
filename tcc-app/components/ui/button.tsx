import React from 'react';
import { 
  TouchableOpacity, 
  Text, 
  StyleSheet, 
  ActivityIndicator, 
  ViewStyle, 
  TextStyle 
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';

interface ButtonProps {
  onPress: () => void;
  title: string;
  loading?: boolean;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'outline';
  style?: ViewStyle;
  textStyle?: TextStyle;
}

export const Button = ({ 
  onPress, 
  title, 
  loading, 
  disabled, 
  variant = 'primary',
  style,
  textStyle 
}: ButtonProps) => {
  const isDisabled = disabled || loading;

  if (variant === 'outline') {
    return (
      <TouchableOpacity 
        onPress={onPress} 
        disabled={isDisabled}
        style={[styles.base, styles.outline, style, isDisabled && styles.disabled]}
      >
        {loading ? (
          <ActivityIndicator color="#4B39EF" />
        ) : (
          <Text style={[styles.text, styles.outlineText, textStyle]}>{title}</Text>
        )}
      </TouchableOpacity>
    );
  }

  return (
    <TouchableOpacity 
      onPress={onPress} 
      disabled={isDisabled}
      style={[styles.base, style]}
    >
      <LinearGradient
        colors={isDisabled ? ['#444', '#333'] : ['#4B39EF', '#5E47FF']}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 0 }}
        style={[styles.gradient, isDisabled && styles.disabled]}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={[styles.text, textStyle]}>{title}</Text>
        )}
      </LinearGradient>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  base: {
    width: '100%',
    height: 56,
    borderRadius: 14,
    overflow: 'hidden',
    marginVertical: 8,
  },
  gradient: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  outline: {
    backgroundColor: 'transparent',
    borderWidth: 2,
    borderColor: '#4B39EF',
    justifyContent: 'center',
    alignItems: 'center',
  },
  text: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
  outlineText: {
    color: '#4B39EF',
  },
  disabled: {
    opacity: 0.6,
  },
});
