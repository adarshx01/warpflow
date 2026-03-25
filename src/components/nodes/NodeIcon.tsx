import React from 'react';
import { 
  FaTelegramPlane, 
  FaSlack, 
  FaAws
} from 'react-icons/fa';
import { 
  SiGoogle, 
  SiGoogledrive, 
  SiGooglesheets, 
  SiPostgresql, 
  SiOpenai, 
  SiGoogleforms, 
  SiGoogledocs
} from 'react-icons/si';
import { 
  MdOutlineEmail, 
  MdWebhook, 
  MdAccessTime, 
  MdTouchApp,
  MdNetworkCheck
} from 'react-icons/md';
import { 
  TbRobot, 
  TbBooks, 
  TbReportAnalytics, 
  TbBrain, 
  TbEye, 
  TbTargetArrow
} from 'react-icons/tb';

interface NodeIconProps {
  type: string;
  fallback: string;
  className?: string;
  size?: number | string;
}

const customIconMap: Record<string, React.ElementType> = {
  // Communication
  'telegram': FaTelegramPlane,
  'slack': FaSlack,

  // Google Workspace
  'google-drive': SiGoogledrive,
  'google-sheets': SiGooglesheets,
  'google-docs': SiGoogledocs,
  'google-forms': SiGoogleforms,
  'gmail': SiGoogle,

  // Triggers
  'manual-trigger': MdTouchApp,
  'schedule': MdAccessTime,
  'webhook': MdWebhook,
  'email-trigger': MdOutlineEmail,

  // AI & ML
  'openai': SiOpenai,
  'gemini': SiGoogle,
  'ai-agent': TbRobot,
  'context-store': TbBooks,

  // ML & CV
  'data-prep': TbReportAnalytics,
  'supervised-train': TbTargetArrow,
  'unsupervised-train': TbBrain,
  'model-inference': MdNetworkCheck,
  'cv-train': TbBrain,
  'cv-inference': TbEye,

  // Data
  'postgresql': SiPostgresql,

  // APIs
  'aws': FaAws,
};

export const NodeIcon: React.FC<NodeIconProps> = ({ type, fallback, className = "", size }) => {
  const IconComponent = customIconMap[type];

  if (IconComponent) {
    return <IconComponent className={className} size={size} />;
  }

  // Fallback to emoji if no icon mapped
  return <span className={className} style={{ fontSize: size }}>{fallback}</span>;
};
