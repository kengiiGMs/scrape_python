// types.ts - Interfaces compartilhadas
export interface PageContent {
    url: string;
    title: string;
    markdown: string;
}

export interface ContactInfo {
    emails: string[];
    phones: string[];
    addresses: string[];
    socialMedia: Record<string, string>;
    contactLinks?: Array<{ url: string; text: string; internal: boolean }>;
}

export interface StoreInfo {
    name?: string;
    description?: string;
    cnpj?: string;
}

export interface ScrapeData {
    url: string;
    metadata: {
        title: string;
        description: string;
        siteName: string;
    };
    contactInfo: ContactInfo;
    storeInfo: StoreInfo;
    institutionalPages: Record<string, PageContent>;
    stats: {
        pagesScraped: number;
        totalInstitutional: number;
    };
}

export interface JobData {
    id: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    url: string;
    startTime: number;
    endTime?: number;
    result?: ScrapeData & { markdownFile: string };
    error?: string;
}
