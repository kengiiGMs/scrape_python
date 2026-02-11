// markdown-generator.ts
import * as fs from 'fs';
import * as path from 'path';
import { ScrapeData } from './types.js'; // ← Importa do arquivo de tipos

export class MarkdownGenerator {

    static generateAndSave(data: ScrapeData, jobId: string): string {
        const markdown = this.generate(data);

        const outputDir = path.join(process.cwd(), 'outputs');
        if (!fs.existsSync(outputDir)) {
            fs.mkdirSync(outputDir, { recursive: true });
        }

        const domain = new URL(data.url).hostname.replace(/\./g, '-');
        const timestamp = new Date().toISOString().split('T')[0];
        const filename = `${domain}_${timestamp}_${jobId.substring(0, 8)}.md`;
        const filepath = path.join(outputDir, filename);

        fs.writeFileSync(filepath, markdown, 'utf-8');
        console.log(`📄 Markdown salvo em: ${filepath}`);

        return filepath;
    }

    static generate(data: ScrapeData): string {
        const sections: string[] = [];

        sections.push(this.generateHeader(data));
        sections.push(this.generateContactSection(data));
        sections.push(this.generateStoreInfo(data));
        sections.push(this.generateInstitutionalContent(data));

        return sections.filter(s => s.trim().length > 0).join('\n\n---\n\n');
    }

    private static generateHeader(data: ScrapeData): string {
        return `# ${data.metadata.title || 'Informações da Loja'}

**Site:** ${data.url}
**Descrição:** ${data.metadata.description || 'Não informado'}
**Nome da Empresa:** ${data.storeInfo.name || 'Não informado'}
**Data da Coleta:** ${new Date().toLocaleDateString('pt-BR')}`;
    }

    private static generateContactSection(data: ScrapeData): string {
        const { contactInfo } = data;
        const lines: string[] = ['## 📞 Informações de Contato'];

        if (contactInfo.emails.length > 0) {
            lines.push('\n**Emails:**');
            contactInfo.emails.forEach(email => lines.push(`- ${email}`));
        }

        if (contactInfo.phones.length > 0) {
            lines.push('\n**Telefones:**');
            contactInfo.phones.forEach(phone => lines.push(`- ${phone}`));
        }

        if (contactInfo.addresses.length > 0) {
            lines.push('\n**Endereços:**');
            contactInfo.addresses.forEach(addr => lines.push(`- ${addr}`));
        }

        const social = contactInfo.socialMedia;
        const socialLinks: string[] = [];
        if (social.whatsapp) socialLinks.push(`- WhatsApp: ${social.whatsapp}`);
        if (social.instagram) socialLinks.push(`- Instagram: ${social.instagram}`);
        if (social.facebook) socialLinks.push(`- Facebook: ${social.facebook}`);
        if (social.twitter) socialLinks.push(`- Twitter: ${social.twitter}`);
        if (social.linkedin) socialLinks.push(`- LinkedIn: ${social.linkedin}`);
        if (social.youtube) socialLinks.push(`- YouTube: ${social.youtube}`);

        if (socialLinks.length > 0) {
            lines.push('\n**Redes Sociais:**');
            lines.push(...socialLinks);
        }

        return lines.join('\n');
    }

    private static generateStoreInfo(data: ScrapeData): string {
        const lines: string[] = ['## 🏢 Dados da Empresa'];

        if (data.storeInfo.name) lines.push(`**Nome:** ${data.storeInfo.name}`);
        if (data.storeInfo.cnpj) lines.push(`**CNPJ:** ${data.storeInfo.cnpj}`);
        if (data.storeInfo.description) lines.push(`**Descrição:** ${data.storeInfo.description}`);

        return lines.length > 1 ? lines.join('\n') : '';
    }

    private static generateInstitutionalContent(data: ScrapeData): string {
        const pages = Object.values(data.institutionalPages);
        if (pages.length === 0) return '';

        const sections = ['## 📄 Conteúdo Institucional', ''];

        pages.forEach(page => {
            sections.push(`### ${page.title}`);
            sections.push('');
            const cleanedContent = this.cleanMarkdown(page.markdown);
            sections.push(cleanedContent);
            sections.push('');
        });

        return sections.join('\n');
    }

    private static cleanMarkdown(markdown: string): string {
        let cleaned = markdown;

        // Remove links mas mantém texto
        cleaned = cleaned.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');

        // Remove URLs soltas (exceto whatsapp)
        cleaned = cleaned.replace(/https?:\/\/[^\s]+(?<!whatsapp|wa\.me)/gi, '');

        // Remove linhas vazias excessivas
        cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
        cleaned = cleaned.split('\n').map(line => line.trimEnd()).join('\n');

        return cleaned.trim();
    }
}
