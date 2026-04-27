import React, { forwardRef, useState } from 'react';
import {
  TextInput,
  TextInputProps,
  View,
  StyleSheet,
  TouchableOpacity,
  ViewStyle,
} from 'react-native';
import { Text } from './Text';
import { useTheme } from '@/hooks/useTheme';

interface InputProps extends TextInputProps {
  label?: string;
  error?: string;
  hint?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  onRightIconPress?: () => void;
  containerStyle?: ViewStyle;
}

export const Input = forwardRef<TextInput, InputProps>(
  (
    {
      label,
      error,
      hint,
      leftIcon,
      rightIcon,
      onRightIconPress,
      containerStyle,
      style,
      editable = true,
      ...props
    },
    ref,
  ) => {
    const { colors, borderRadius: br, spacing, fontFamily, fontSize } = useTheme();
    const [isFocused, setIsFocused] = useState(false);

    const borderColor = error
      ? colors.error
      : isFocused
        ? colors.primary
        : colors.border;

    return (
      <View style={[styles.wrapper, containerStyle]}>
        {label && (
          <Text variant="caption" color={error ? colors.error : colors.textSecondary} style={styles.label}>
            {label}
          </Text>
        )}
        <View
          style={[
            styles.inputContainer,
            {
              borderColor,
              borderRadius: br.lg,
              backgroundColor: editable ? colors.surface : colors.surfaceVariant,
            },
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
              leftIcon ? { paddingLeft: 0 } : undefined,
              rightIcon ? { paddingRight: 0 } : undefined,
              style,
            ]}
            placeholderTextColor={colors.textDisabled}
            editable={editable}
            onFocus={(e) => {
              setIsFocused(true);
              props.onFocus?.(e);
            }}
            onBlur={(e) => {
              setIsFocused(false);
              props.onBlur?.(e);
            }}
            accessibilityLabel={label ?? props.placeholder}
            {...props}
          />
          {rightIcon && (
            <TouchableOpacity
              onPress={onRightIconPress}
              disabled={!onRightIconPress}
              hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
            >
              <View style={styles.rightIcon}>{rightIcon}</View>
            </TouchableOpacity>
          )}
        </View>
        {(error || hint) && (
          <Text
            variant="caption"
            color={error ? colors.error : colors.textSecondary}
            style={styles.helperText}
          >
            {error ?? hint}
          </Text>
        )}
      </View>
    );
  },
);

Input.displayName = 'Input';

const styles = StyleSheet.create({
  wrapper: {
    marginBottom: 16,
  },
  label: {
    marginBottom: 6,
    marginLeft: 4,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1.5,
    paddingHorizontal: 14,
    minHeight: 50,
  },
  input: {
    flex: 1,
    paddingVertical: 12,
    paddingHorizontal: 0,
  },
  leftIcon: {
    marginRight: 10,
  },
  rightIcon: {
    marginLeft: 10,
  },
  helperText: {
    marginTop: 4,
    marginLeft: 4,
  },
});
