/**
 * Skeleton Loading Components
 * ===========================
 * Placeholder components shown while content is loading.
 */

import React from 'react';
import { Box, Skeleton as MuiSkeleton, Card, CardContent, CardHeader } from '@mui/material';

/**
 * Text Skeleton - For text content
 */
export function TextSkeleton({ lines = 3, width = '100%' }) {
  return (
    <Box sx={{ width }}>
      {Array.from({ length: lines }).map((_, i) => (
        <MuiSkeleton
          key={i}
          variant="text"
          width={i === lines - 1 ? '60%' : '100%'}
          height={24}
          sx={{ mb: 0.5 }}
        />
      ))}
    </Box>
  );
}

/**
 * Card Skeleton - For card components
 */
export function CardSkeleton({ hasImage = false, hasActions = false }) {
  return (
    <Card sx={{ maxWidth: 345, width: '100%' }}>
      {hasImage && (
        <MuiSkeleton
          variant="rectangular"
          height={140}
          animation="wave"
        />
      )}
      <CardHeader
        avatar={
          <MuiSkeleton
            variant="circular"
            width={40}
            height={40}
            animation="wave"
          />
        }
        title={<MuiSkeleton variant="text" width="60%" animation="wave" />}
        subheader={<MuiSkeleton variant="text" width="40%" animation="wave" />}
      />
      <CardContent>
        <TextSkeleton lines={3} />
      </CardContent>
      {hasActions && (
        <Box sx={{ p: 2, display: 'flex', gap: 1 }}>
          <MuiSkeleton variant="rectangular" width={80} height={36} animation="wave" />
          <MuiSkeleton variant="rectangular" width={80} height={36} animation="wave" />
        </Box>
      )}
    </Card>
  );
}

/**
 * List Skeleton - For list items
 */
export function ListSkeleton({ items = 5, hasAvatar = true, hasSecondary = true }) {
  return (
    <Box>
      {Array.from({ length: items }).map((_, i) => (
        <Box
          key={i}
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 2,
            p: 2,
            borderBottom: '1px solid',
            borderColor: 'divider'
          }}
        >
          {hasAvatar && (
            <MuiSkeleton
              variant="circular"
              width={40}
              height={40}
              animation="wave"
            />
          )}
          <Box sx={{ flex: 1 }}>
            <MuiSkeleton
              variant="text"
              width={`${60 + Math.random() * 30}%`}
              height={24}
              animation="wave"
            />
            {hasSecondary && (
              <MuiSkeleton
                variant="text"
                width={`${40 + Math.random() * 20}%`}
                height={20}
                animation="wave"
              />
            )}
          </Box>
        </Box>
      ))}
    </Box>
  );
}

/**
 * Table Skeleton - For table content
 */
export function TableSkeleton({ rows = 5, columns = 4 }) {
  return (
    <Box>
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          gap: 2,
          p: 2,
          borderBottom: '2px solid',
          borderColor: 'divider',
          backgroundColor: 'action.hover'
        }}
      >
        {Array.from({ length: columns }).map((_, i) => (
          <MuiSkeleton
            key={`header-${i}`}
            variant="text"
            width={`${100 / columns}%`}
            height={24}
            animation="wave"
          />
        ))}
      </Box>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <Box
          key={rowIndex}
          sx={{
            display: 'flex',
            gap: 2,
            p: 2,
            borderBottom: '1px solid',
            borderColor: 'divider'
          }}
        >
          {Array.from({ length: columns }).map((_, colIndex) => (
            <MuiSkeleton
              key={`cell-${rowIndex}-${colIndex}`}
              variant="text"
              width={`${100 / columns}%`}
              height={20}
              animation="wave"
            />
          ))}
        </Box>
      ))}
    </Box>
  );
}

/**
 * Chat Skeleton - For chat messages
 */
export function ChatSkeleton({ messages = 4 }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, p: 2 }}>
      {Array.from({ length: messages }).map((_, i) => {
        const isUser = i % 2 === 0;
        return (
          <Box
            key={i}
            sx={{
              display: 'flex',
              justifyContent: isUser ? 'flex-end' : 'flex-start',
              gap: 1
            }}
          >
            {!isUser && (
              <MuiSkeleton
                variant="circular"
                width={32}
                height={32}
                animation="wave"
              />
            )}
            <MuiSkeleton
              variant="rectangular"
              width={`${40 + Math.random() * 30}%`}
              height={60 + Math.random() * 40}
              animation="wave"
              sx={{ borderRadius: 2 }}
            />
            {isUser && (
              <MuiSkeleton
                variant="circular"
                width={32}
                height={32}
                animation="wave"
              />
            )}
          </Box>
        );
      })}
    </Box>
  );
}

/**
 * Dashboard Skeleton - For dashboard widgets
 */
export function DashboardSkeleton() {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Stats row */}
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i} sx={{ flex: '1 1 200px', minWidth: 200 }}>
            <CardContent>
              <MuiSkeleton variant="text" width="40%" height={20} animation="wave" />
              <MuiSkeleton variant="text" width="60%" height={40} animation="wave" />
              <MuiSkeleton variant="text" width="30%" height={16} animation="wave" />
            </CardContent>
          </Card>
        ))}
      </Box>
      {/* Chart area */}
      <Card>
        <CardContent>
          <MuiSkeleton variant="text" width="20%" height={28} animation="wave" />
          <MuiSkeleton
            variant="rectangular"
            width="100%"
            height={300}
            animation="wave"
            sx={{ mt: 2, borderRadius: 1 }}
          />
        </CardContent>
      </Card>
      {/* Table */}
      <Card>
        <CardContent>
          <MuiSkeleton variant="text" width="15%" height={28} animation="wave" />
          <Box sx={{ mt: 2 }}>
            <TableSkeleton rows={5} columns={5} />
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}

/**
 * File Browser Skeleton
 */
export function FileBrowserSkeleton({ items = 8 }) {
  return (
    <Box>
      {/* Toolbar */}
      <Box sx={{ display: 'flex', gap: 2, p: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
        <MuiSkeleton variant="rectangular" width={120} height={36} animation="wave" />
        <MuiSkeleton variant="rectangular" width={200} height={36} animation="wave" sx={{ flex: 1 }} />
        <MuiSkeleton variant="circular" width={36} height={36} animation="wave" />
      </Box>
      {/* File list */}
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, p: 2 }}>
        {Array.from({ length: items }).map((_, i) => (
          <Box
            key={i}
            sx={{
              width: 120,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 1
            }}
          >
            <MuiSkeleton
              variant="rectangular"
              width={64}
              height={64}
              animation="wave"
              sx={{ borderRadius: 1 }}
            />
            <MuiSkeleton variant="text" width="80%" height={20} animation="wave" />
          </Box>
        ))}
      </Box>
    </Box>
  );
}

/**
 * Generic loading wrapper
 */
export function SkeletonWrapper({ loading, skeleton, children }) {
  if (loading) {
    return skeleton;
  }
  return children;
}

export default {
  TextSkeleton,
  CardSkeleton,
  ListSkeleton,
  TableSkeleton,
  ChatSkeleton,
  DashboardSkeleton,
  FileBrowserSkeleton,
  SkeletonWrapper
};
