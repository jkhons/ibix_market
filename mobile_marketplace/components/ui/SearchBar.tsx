import React, { forwardRef, useState } from 'react';
import {
  View,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  TextInputProps,
  ViewStyle,
} from 'react-native';
import { Text } from './Text';
import { useTheme } from '@/hooks/useTheme';

interface SearchBarProps extends TextInputProps {
  onSearch?: (query: string) => void;
  onClear?: () => void;
  containerStyle?: ViewStyle;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const SearchBar = forwardRef<TextInput, SearchBarProps>(
  ({ onSearch, onClear, containerStyle, leftIcon, rightIcon, value, ...props }, ref) => {
    const { colors, borderRadius: br, spacing, fontFamily, fontSize } = useTheme();
    const [isFocused, setIsFocused] = useState(false);

    const handleSubmit = () => {
      if (value && onSearch) onSearch(value);
    };

    return (
      <View
        style={[
          styles.container,
          {
            backgroundColor: colors.surfaceVariant,
            borderRadius: br.xl,
            borderColor: isFocused ? colors.primary : colors.transparent,
            borderWidth: 1.5,
          },
          containerStyle,
        ]}
      >
        {leftIcon && <View style={styles.leftIcon}>{leftIcon}</View>}
        <TextInput
          ref={ref}
          style={[
            styles.input,
            {
              color: colors.textPrimary,
              fontFamily: fontFamily.regular,
              fontSize: fontSize.md,
            },
          ]}
          placeholderTextColor={colors.textDisabled}
          placeholder="Buscar produtos, lojas..."
          returnKeyType="search"
          onSubmitEditing={handleSubmit}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          value={value}
          accessibilityLabel="Campo de busca"
          accessibilityRole="search"
          {...props}
        />
        {value && value.length > 0 && onClear && (
          <TouchableOpacity onPress={onClear} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
            <Text variant="caption" color={colors.textSecondary}>
              Limpar
            </Text>
          </TouchableOpacity>
        )}
        {rightIcon && <View style={styles.rightIcon}>{rightIcon}</View>}
      </View>
    );
  },
);

SearchBar.displayName = 'SearchBar';

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    height: 48,
  },
  leftIcon: {
    marginRight: 10,
  },
  rightIcon: {
    marginLeft: 10,
  },
  input: {
    flex: 1,
    paddingVertical: 0,
  },
});
