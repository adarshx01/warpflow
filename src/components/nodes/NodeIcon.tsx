import React from 'react';
import { 
  FaTelegramPlane, 
  FaSlack, 
  FaDiscord, 
  FaGithub, 
  FaStripe, 
  FaAws,
  FaUsers
} from 'react-icons/fa';
import { 
  SiGoogle, 
  SiGoogledrive, 
  SiGooglesheets, 
  SiPostgresql, 
  SiMongodb, 
  SiMysql, 
  SiRedis, 
  SiOpenai, 
  SiAirtable, 
  SiGoogleforms, 
  SiGoogledocs,
  SiAnthropic,
  SiHuggingface
} from 'react-icons/si';
import { 
  MdOutlineEmail, 
  MdSms, 
  MdWebhook, 
  MdAccessTime, 
  MdTouchApp, 
  MdArticle, 
  MdDataObject,
  MdFilterAlt,
  MdTransform,
  MdSort,
  MdBarChart,
  MdLoop,
  MdCallSplit,
  MdCallMerge,
  MdPauseCircleOutline,
  MdAltRoute,
  MdNetworkCheck
} from 'react-icons/md';
import { 
  TbRobot, 
  TbBooks, 
  TbReportAnalytics, 
  TbBrain, 
  TbEye, 
  TbTargetArrow,
  TbWand
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
  'discord': FaDiscord,
  'teams': FaUsers,
  'email': MdOutlineEmail,
  'sms': MdSms,

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
  'news-trigger': MdArticle,

  // AI & ML
  'openai': SiOpenai,
  'gemini': SiGoogle,
  'anthropic': SiAnthropic,
  'huggingface': SiHuggingface,
  'ai-agent': TbRobot,
  'context-store': TbBooks,
  'image-gen': TbWand,

  // ML & CV
  'data-prep': TbReportAnalytics,
  'supervised-train': TbTargetArrow,
  'unsupervised-train': TbBrain,
  'model-inference': MdNetworkCheck,
  'cv-train': TbBrain,
  'cv-inference': TbEye,

  // Data
  'postgresql': SiPostgresql,
  'mongodb': SiMongodb,
  'redis': SiRedis,
  'mysql': SiMysql,
  'airtable': SiAirtable,

  // Processing & Logic
  'transform': MdTransform,
  'filter': MdFilterAlt,
  'aggregate': MdBarChart,
  'sort': MdSort,
  'json': MdDataObject,
  'if-condition': MdAltRoute,
  'switch': MdAltRoute,
  'loop': MdLoop,
  'split': MdCallSplit,
  'merge': MdCallMerge,
  'wait': MdPauseCircleOutline,

  // APIs
  'http': MdNetworkCheck,
  'rest-api': MdNetworkCheck,
  'github': FaGithub,
  'stripe': FaStripe,
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
