"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useMemo,
  useRef,
} from "react";
import { CompanyProfile, companyApi } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { getActiveBrandId, setActiveBrandId as persistActiveBrandId } from "@/lib/activeBrand";

interface BrandContextType {
  brands: CompanyProfile[];
  activeBrand: CompanyProfile | null;
  activeBrandId: string | null;
  isLoading: boolean;
  error: string | null;
  setActiveBrandId: (id: string | null) => void;
  refreshBrands: (targetActiveId?: string | null) => Promise<CompanyProfile[]>;
}

const BrandContext = createContext<BrandContextType | undefined>(undefined);

export function BrandProvider({ children }: { children: React.ReactNode }) {
  const { user, isLoading: authLoading } = useAuth();

  const [brands, setBrands] = useState<CompanyProfile[]>([]);
  const [activeBrandId, setActiveBrandIdState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const inFlightPromiseRef = useRef<Promise<CompanyProfile[]> | null>(null);
  const lastFetchedUserIdRef = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    if (authLoading) return;

    if (!user) {
      lastFetchedUserIdRef.current = null;
      inFlightPromiseRef.current = null;
      void Promise.resolve().then(() => {
        if (!cancelled) {
          setBrands([]);
          setActiveBrandIdState(null);
          setError(null);
          setIsLoading(false);
        }
      });
      return;
    }

    const currentUserId = user.id;

    // Already loaded for this authenticated user: keep existing state
    if (lastFetchedUserIdRef.current === currentUserId) {
      void Promise.resolve().then(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });
      return;
    }

    async function loadBrands() {
      setIsLoading(true);
      setError(null);

      try {
        let promise = inFlightPromiseRef.current;
        if (!promise) {
          promise = companyApi.list();
          inFlightPromiseRef.current = promise;
        }

        const list = await promise;
        if (cancelled) return;

        setBrands(list);
        lastFetchedUserIdRef.current = currentUserId;

        // Resolve active brand from localStorage or fallback to first owned brand
        let current = getActiveBrandId(currentUserId);
        if ((!current || !list.some((b) => b.id === current)) && list.length > 0) {
          current = list[0].id;
          persistActiveBrandId(currentUserId, current);
        } else if (!list.length) {
          current = null;
          persistActiveBrandId(currentUserId, null);
        }

        setActiveBrandIdState(current);
      } catch (err: unknown) {
        if (cancelled) return;
        const msg = err instanceof Error ? err.message : "Failed to load brand profiles";
        setError(msg);
        setBrands([]);
      } finally {
        inFlightPromiseRef.current = null;
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadBrands();

    return () => {
      cancelled = true;
    };
  }, [authLoading, user]);

  const setActiveBrandId = useCallback(
    (id: string | null) => {
      setActiveBrandIdState(id);
      if (user?.id) {
        persistActiveBrandId(user.id, id);
      }
    },
    [user]
  );

  const refreshBrands = useCallback(
    async (targetActiveId?: string | null): Promise<CompanyProfile[]> => {
      if (!user) return [];
      const currentUserId = user.id;

      setIsLoading(true);
      setError(null);

      try {
        const promise = companyApi.list();
        inFlightPromiseRef.current = promise;
        const list = await promise;

        setBrands(list);
        lastFetchedUserIdRef.current = currentUserId;

        let nextActiveId = targetActiveId;
        if (nextActiveId === undefined) {
          nextActiveId = getActiveBrandId(currentUserId);
        }

        if ((!nextActiveId || !list.some((b) => b.id === nextActiveId)) && list.length > 0) {
          nextActiveId = list[0].id;
        } else if (!list.length) {
          nextActiveId = null;
        }

        setActiveBrandIdState(nextActiveId);
        persistActiveBrandId(currentUserId, nextActiveId);

        return list;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Failed to refresh brand profiles";
        setError(msg);
        throw err;
      } finally {
        inFlightPromiseRef.current = null;
        setIsLoading(false);
      }
    },
    [user]
  );

  const activeBrand = useMemo(() => {
    return brands.find((b) => b.id === activeBrandId) ?? null;
  }, [brands, activeBrandId]);

  const value = useMemo(
    () => ({
      brands,
      activeBrand,
      activeBrandId,
      isLoading,
      error,
      setActiveBrandId,
      refreshBrands,
    }),
    [brands, activeBrand, activeBrandId, isLoading, error, setActiveBrandId, refreshBrands]
  );

  return <BrandContext.Provider value={value}>{children}</BrandContext.Provider>;
}

export function useBrand(): BrandContextType {
  const context = useContext(BrandContext);
  if (!context) {
    throw new Error("useBrand must be used within a BrandProvider");
  }
  return context;
}
