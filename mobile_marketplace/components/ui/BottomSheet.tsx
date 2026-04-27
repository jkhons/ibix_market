import React, { forwardRef, useCallback, useMemo } from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import GorhomBottomSheet, {
  BottomSheetBackdrop,
  BottomSheetBackdropProps,
  BottomSheetView,
} from '@gorhom/bottom-sheet';
import { useTheme } from '@/hooks/useTheme';

interface BottomSheetProps {
  children: React.ReactNode;
  snapPoints?: (string | number)[];
  onClose?: () => void;
  enablePanDownToClose?: boolean;
  style?: ViewStyle;
}

export const AppBottomSheet = forwardRef<GorhomBottomSheet, BottomSheetProps>(
  ({ children, snapPoints: sp, onClose, enablePanDownToClose = true, style }, ref) => {
    const { colors, borderRadius: br } = useTheme();

    const snapPoints = useMemo(() => sp ?? ['25%', '50%'], [sp]);

    const renderBackdrop = useCallback(
      (props: BottomSheetBackdropProps) => (
        <BottomSheetBackdrop {...props} disappearsOnIndex={-1} appearsOnIndex={0} opacity={0.5} />
      ),
      [],
    );

    return (
      <GorhomBottomSheet
        ref={ref}
        index={-1}
        snapPoints={snapPoints}
        enablePanDownToClose={enablePanDownToClose}
        onClose={onClose}
        backdropComponent={renderBackdrop}
        handleIndicatorStyle={{ backgroundColor: colors.gray400, width: 40 }}
        backgroundStyle={{
          backgroundColor: colors.surface,
          borderTopLeftRadius: br['2xl'],
          borderTopRightRadius: br['2xl'],
        }}
        style={style}
      >
        <BottomSheetView style={styles.content}>{children}</BottomSheetView>
      </GorhomBottomSheet>
    );
  },
);

AppBottomSheet.displayName = 'AppBottomSheet';

const styles = StyleSheet.create({
  content: {
    flex: 1,
    paddingHorizontal: 16,
    paddingBottom: 16,
  },
});
