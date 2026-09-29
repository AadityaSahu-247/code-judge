import React, { useEffect, useRef, useState } from 'react';

const VIDEO_URL =
  'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260729_102822_0e6c87e8-c141-4744-bf32-ad30db296371.mp4';

interface BackgroundVideoProps {
  interactiveScroll?: boolean;
}

export const BackgroundVideo: React.FC<BackgroundVideoProps> = ({ interactiveScroll = false }) => {
  const [loaded, setLoaded] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const progressRef = useRef(0);
  const smoothedRef = useRef(0);
  const velocityRef = useRef(0);

  const framesRef = useRef<ImageBitmap[]>([]);
  const isCachedRef = useRef(false);

  // ── 1. Scroll listener ───────────────────
  useEffect(() => {
    if (!interactiveScroll) return;

    const update = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      if (max > 0) {
        progressRef.current = Math.min(1, Math.max(0, window.scrollY / max));
      }
    };

    window.addEventListener('scroll', update, { passive: true });
    update();
    return () => window.removeEventListener('scroll', update);
  }, [interactiveScroll]);

  // ── 2. Pre-extract 60 keyframes into ImageBitmaps for 60 FPS instant canvas ──
  useEffect(() => {
    if (!interactiveScroll) return;
    let canceled = false;

    const extractFrames = async () => {
      try {
        const offscreenVid = document.createElement('video');
        offscreenVid.src = VIDEO_URL;
        offscreenVid.muted = true;
        offscreenVid.playsInline = true;
        offscreenVid.preload = 'auto';
        offscreenVid.crossOrigin = 'anonymous';

        await new Promise<void>((resolve, reject) => {
          offscreenVid.addEventListener('loadedmetadata', () => resolve(), { once: true });
          offscreenVid.addEventListener('error', reject, { once: true });
          offscreenVid.load();
        });

        const dur = offscreenVid.duration;
        if (!dur || !isFinite(dur)) return;

        const count = 60; // 60 frames for butter-smooth 60fps scrubbing
        const tw = 854;
        const th = Math.round(((offscreenVid.videoHeight || 540) / (offscreenVid.videoWidth || 960)) * tw);

        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = tw;
        tempCanvas.height = th;
        const ctx = tempCanvas.getContext('2d');
        if (!ctx) return;

        const extracted: ImageBitmap[] = [];

        for (let i = 0; i < count; i++) {
          if (canceled) return;
          const time = (i / (count - 1)) * (dur - 0.05);

          await new Promise<void>((res) => {
            offscreenVid.addEventListener('seeked', () => res(), { once: true });
            offscreenVid.currentTime = time;
          });

          ctx.drawImage(offscreenVid, 0, 0, tw, th);
          const bmp = await createImageBitmap(tempCanvas);
          extracted.push(bmp);
        }

        if (!canceled && extracted.length === count) {
          framesRef.current = extracted;
          isCachedRef.current = true;
          setLoaded(true);
        }
      } catch {
        setLoaded(true);
      }
    };

    extractFrames();
    return () => {
      canceled = true;
    };
  }, [interactiveScroll]);

  // ── 3. 60 FPS Smooth Render Loop ───────────────────
  useEffect(() => {
    let animId: number;

    const drawCover = (
      ctx: CanvasRenderingContext2D,
      source: CanvasImageSource,
      sw: number,
      sh: number,
      dw: number,
      dh: number
    ) => {
      const scale = Math.max(dw / sw, dh / sh);
      const nw = sw * scale;
      const nh = sh * scale;
      ctx.clearRect(0, 0, dw, dh);
      ctx.drawImage(
        source,
        Math.round((dw - nw) / 2),
        Math.round((dh - nh) / 2),
        Math.round(nw),
        Math.round(nh)
      );
    };

    const render = () => {
      const target = progressRef.current;
      const diff = target - smoothedRef.current;

      // Inertia spring physics
      velocityRef.current = velocityRef.current * 0.75 + diff * 0.06;
      smoothedRef.current += velocityRef.current;

      const canvas = canvasRef.current;
      const ctx = canvas?.getContext('2d');

      if (canvas && ctx) {
        const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
        const w = Math.round(window.innerWidth * dpr);
        const h = Math.round(window.innerHeight * dpr);

        if (canvas.width !== w || canvas.height !== h) {
          canvas.width = w;
          canvas.height = h;
        }

        if (isCachedRef.current && framesRef.current.length > 0) {
          const count = framesRef.current.length;
          const idx = Math.min(count - 1, Math.max(0, Math.floor(smoothedRef.current * count)));
          const bmp = framesRef.current[idx];
          if (bmp) {
            drawCover(ctx, bmp, bmp.width, bmp.height, w, h);
          }
        } else {
          const vid = videoRef.current;
          if (vid && vid.readyState >= 2 && vid.duration && isFinite(vid.duration)) {
            const targetTime = smoothedRef.current * (vid.duration - 0.05);
            if (!vid.seeking && Math.abs(vid.currentTime - targetTime) > 0.02) {
              vid.currentTime = targetTime;
            }
            if (vid.videoWidth > 0) {
              drawCover(ctx, vid, vid.videoWidth, vid.videoHeight, w, h);
            }
          }
        }
      }

      animId = requestAnimationFrame(render);
    };

    if (interactiveScroll) {
      animId = requestAnimationFrame(render);
    }

    return () => {
      if (animId) cancelAnimationFrame(animId);
    };
  }, [interactiveScroll]);

  return (
    <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none bg-[#0a0a0a]">
      {/* 1. Poster fallback */}
      <img
        src="/hero-poster.jpg"
        alt=""
        className="absolute inset-0 w-full h-full object-cover z-20 transition-opacity duration-700"
        style={{ opacity: loaded ? 0 : 1 }}
      />

      {interactiveScroll ? (
        <>
          {/* 2. Hidden background video for initial seek fallback */}
          <video
            ref={videoRef}
            src={VIDEO_URL}
            muted
            playsInline
            preload="auto"
            crossOrigin="anonymous"
            onCanPlay={() => setLoaded(true)}
            className="absolute inset-0 w-full h-full object-cover opacity-0 pointer-events-none"
          />

          {/* 3. 60 FPS Instant Canvas */}
          <canvas
            ref={canvasRef}
            className="absolute inset-0 w-full h-full z-10 transition-opacity duration-500"
            style={{ opacity: loaded ? 1 : 0 }}
          />
        </>
      ) : (
        /* Autoplay video for non-interactive mode */
        <video
          ref={videoRef}
          src={VIDEO_URL}
          muted
          loop
          autoPlay
          playsInline
          preload="auto"
          crossOrigin="anonymous"
          onCanPlay={() => setLoaded(true)}
          className="absolute inset-0 w-full h-full object-cover z-10 transition-opacity duration-700"
          style={{ opacity: loaded ? 1 : 0 }}
        />
      )}
    </div>
  );
};
