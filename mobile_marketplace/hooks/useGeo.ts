import { useCallback } from 'react';
import * as Location from 'expo-location';

import { useGeoStore, type GeoLocation } from '@/store/geoStore';
import geoService from '@/services/geoService';

export type GeoRequestOutcome =
  | { status: 'granted'; location: GeoLocation }
  | { status: 'denied' }
  | { status: 'error'; message: string };

export function useGeo() {
  const location = useGeoStore((s) => s.location);
  const isHydrated = useGeoStore((s) => s.isHydrated);
  const permissionDenied = useGeoStore((s) => s.permissionDenied);
  const setLocation = useGeoStore((s) => s.setLocation);
  const setPermissionDenied = useGeoStore((s) => s.setPermissionDenied);
  const clearLocation = useGeoStore((s) => s.clearLocation);

  const requestAndUpdate = useCallback(async (): Promise<GeoRequestOutcome> => {
    try {
      const { status: permission } = await Location.requestForegroundPermissionsAsync();
      if (permission !== 'granted') {
        setPermissionDenied(true);
        return { status: 'denied' };
      }
      const pos = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });
      const lat = pos.coords.latitude;
      const lng = pos.coords.longitude;

      let cidade: string | undefined;
      let uf: string | undefined;
      try {
        const reverse = await geoService.reverseGeo(lat, lng);
        cidade = reverse.cidade ?? undefined;
        uf = reverse.uf ?? undefined;
      } catch {
        try {
          const nearest = await geoService.nearestCity(lat, lng);
          cidade = nearest.cidade ?? undefined;
          uf = nearest.uf ?? undefined;
        } catch {}
      }

      const next: GeoLocation = {
        lat,
        lng,
        cidade,
        uf,
        source: 'gps',
        updated_at: Date.now(),
      };
      setLocation(next);
      return { status: 'granted', location: next };
    } catch (err: unknown) {
      return { status: 'error', message: String(err) };
    }
  }, [setLocation, setPermissionDenied]);

  const setManualLocation = useCallback(
    (city: { cidade: string; uf: string; lat?: number | null; lng?: number | null }) => {
      if (!Number.isFinite(city.lat) || !Number.isFinite(city.lng)) return;
      const next: GeoLocation = {
        lat: Number(city.lat),
        lng: Number(city.lng),
        cidade: city.cidade,
        uf: city.uf,
        source: 'manual',
        updated_at: Date.now(),
      };
      setLocation(next);
    },
    [setLocation],
  );

  return {
    location,
    isHydrated,
    permissionDenied,
    requestAndUpdate,
    setManualLocation,
    clearLocation,
  };
}
