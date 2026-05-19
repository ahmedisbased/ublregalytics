import { useState } from 'react';
import { IoClose } from 'react-icons/io5';
import api from '../../services/api';
import './focus-mode-modal.scss';

interface FocusModeModalProps {
    onClose: () => void;
    onDisable: () => void;
}

type DocxModule = typeof import('docx');

const sanitizeFileName = (value: string) => {
    const cleaned = value.trim().replace(/[\\/:*?\\"<>|]/g, '').replace(/\s+/g, '-');
    return cleaned || 'summary-report';
};

const buildFallbackFileName = (companyName: string, air: string) => {
    if (companyName) {
        return `${companyName}-summary`;
    }

    if (air) {
        return `${air}-summary`;
    }

    return 'summary-report';
};

const ensureDocxExtension = (fileName: string) => {
    return fileName.toLowerCase().endsWith('.docx') ? fileName : `${fileName}.docx`;
};

const FocusModeModal = ({ onClose, onDisable }: FocusModeModalProps) => {
    const [companyName, setCompanyName] = useState('');
    const [air, setAir] = useState('');
    const [isGenerating, setIsGenerating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const summaryDownloadUrl = 'https://bca-chatbot-fkbfd2cfa2b9gvh0.uaenorth-01.azurewebsites.net/summary';

    const handleSubmit: React.FormEventHandler<HTMLFormElement> = (event) => {
        event.preventDefault();
        onClose();
    };

    const handleDisableClick = () => {
        setCompanyName('');
        setAir('');
        setError(null);
        onDisable();
    };

    const handleGenerateSummary = async () => {
        setError(null);

        const trimmedCompanyName = companyName.trim();
        const trimmedAir = air.trim();

        if (!trimmedCompanyName || !trimmedAir) {
            setError('Please provide both the company name and AIR to generate a summary.');
            return;
        }

        if (!summaryDownloadUrl) {
            setError('Summary export service is not configured.');
            return;
        }

        setIsGenerating(true);
        try {
            // Expect JSON directly from backend
            const response = await api.post(
                summaryDownloadUrl,
                { company: trimmedCompanyName, year: trimmedAir },
                {
                    responseType: 'json',
                    headers: { Accept: 'application/json' },
                }
            );

            const summaryPayload = response?.data?.summary;
            const summaryText: string | undefined =
                typeof summaryPayload === 'string'
                    ? summaryPayload
                    : (summaryPayload as { summary?: string } | undefined)?.summary;

            if (!summaryText) {
                throw new Error('Server returned JSON without summary text.');
            }

            const docx = (await import('docx')) as DocxModule;
            const { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, LevelFormat } = docx;

            type ParagraphInstance = InstanceType<typeof Paragraph>;
            type TextRunInstance = InstanceType<typeof TextRun>;

            const parseInlineMarkdown = (input: string): TextRunInstance[] => {
                if (!input) {
                    return [new TextRun({ text: '' })];
                }

                const runs: TextRunInstance[] = [];
                const boldPattern = /\*\*(.+?)\*\*/g;
                let cursor = 0;
                let match: RegExpExecArray | null;

                while ((match = boldPattern.exec(input)) !== null) {
                    if (match.index > cursor) {
                        runs.push(new TextRun({ text: input.slice(cursor, match.index) }));
                    }

                    runs.push(
                        new TextRun({
                            text: match[1],
                            bold: true,
                        })
                    );

                    cursor = match.index + match[0].length;
                }

                if (cursor < input.length) {
                    runs.push(new TextRun({ text: input.slice(cursor) }));
                }

                return runs.length > 0 ? runs : [new TextRun({ text: input })];
            };

            const headingLevels: Record<number, typeof HeadingLevel[keyof typeof HeadingLevel]> = {
                1: HeadingLevel.HEADING_1,
                2: HeadingLevel.HEADING_2,
                3: HeadingLevel.HEADING_3,
                4: HeadingLevel.HEADING_4,
                5: HeadingLevel.HEADING_5,
                6: HeadingLevel.HEADING_6,
            };

            const paragraphs: ParagraphInstance[] = [];
            const lines = summaryText.replace(/\r\n/g, '\n').split('\n');
            let inCodeBlock = false;

            lines.forEach((rawLine) => {
                const trimmedRight = rawLine.replace(/\s+$/, '');
                const trimmed = trimmedRight.trim();

                if (trimmed.startsWith('`')) {
                    inCodeBlock = !inCodeBlock;
                    if (!inCodeBlock) {
                        paragraphs.push(new Paragraph({ text: '' }));
                    }
                    return;
                }

                if (inCodeBlock) {
                    paragraphs.push(
                        new Paragraph({
                            style: 'CodeBlock',
                            children: [
                                new TextRun({
                                    text: rawLine || ' ',
                                    font: 'Consolas',
                                }),
                            ],
                        })
                    );
                    return;
                }

                if (trimmed === '') {
                    paragraphs.push(new Paragraph({ text: '' }));
                    return;
                }

                if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
                    paragraphs.push(new Paragraph({ thematicBreak: true }));
                    return;
                }

                const headingMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
                if (headingMatch) {
                    const level = Math.min(headingMatch[1].length, 6);
                    const content = headingMatch[2].trim();
                    paragraphs.push(
                        new Paragraph({
                            heading: headingLevels[level],
                            children: parseInlineMarkdown(content),
                        })
                    );
                    return;
                }

                if (/^(\*|-|\+)\s+/.test(trimmed)) {
                    const content = trimmed.replace(/^(\*|-|\+)\s+/, '');
                    paragraphs.push(
                        new Paragraph({
                            children: parseInlineMarkdown(content),
                            numbering: { reference: 'bullet-list', level: 0 },
                        })
                    );
                    return;
                }

                if (/^\d+\.\s+/.test(trimmed)) {
                    const content = trimmed.replace(/^\d+\.\s+/, '');
                    paragraphs.push(
                        new Paragraph({
                            children: parseInlineMarkdown(content),
                            numbering: { reference: 'numbered-list', level: 0 },
                        })
                    );
                    return;
                }

                if (trimmed.startsWith('>')) {
                    const content = trimmed.replace(/^>\s*/, '');
                    paragraphs.push(
                        new Paragraph({
                            style: 'Quote',
                            children: parseInlineMarkdown(content),
                        })
                    );
                    return;
                }

                paragraphs.push(
                    new Paragraph({
                        children: parseInlineMarkdown(trimmedRight),
                    })
                );
            });

            if (paragraphs.length === 0) {
                paragraphs.push(
                    new Paragraph({
                        children: [new TextRun({ text: 'Summary unavailable.' })],
                    })
                );
            }

            const doc = new Document({
                styles: {
                    default: {
                        document: {
                            run: {
                                font: 'Calibri',
                                size: 24,
                            },
                            paragraph: {
                                spacing: { after: 240 },
                            },
                        },
                    },
                    paragraphStyles: [
                        {
                            id: 'CodeBlock',
                            name: 'Code Block',
                            basedOn: 'Normal',
                            next: 'Normal',
                            run: {
                                font: 'Consolas',
                                size: 22,
                            },
                            paragraph: {
                                spacing: { before: 120, after: 120 },
                                shading: { fill: 'EDEDED' },
                            },
                        },
                        {
                            id: 'Quote',
                            name: 'Quote',
                            basedOn: 'Normal',
                            next: 'Normal',
                            run: {
                                italics: true,
                            },
                            paragraph: {
                                spacing: { before: 120, after: 120 },
                                indent: { left: 720 },
                            },
                        },
                    ],
                },
                numbering: {
                    config: [
                        {
                            reference: 'numbered-list',
                            levels: [
                                {
                                    level: 0,
                                    format: LevelFormat.DECIMAL,
                                    text: '%1.',
                                    alignment: AlignmentType.START,
                                    style: {
                                        paragraph: {
                                            indent: { left: 720, hanging: 360 },
                                        },
                                    },
                                },
                            ],
                        },
                        {
                            reference: 'bullet-list',
                            levels: [
                                {
                                    level: 0,
                                    format: LevelFormat.BULLET,
                                    text: '\u2022',
                                    alignment: AlignmentType.START,
                                    style: {
                                        paragraph: {
                                            indent: { left: 720, hanging: 360 },
                                        },
                                    },
                                },
                            ],
                        },
                    ],
                },
                sections: [
                    {
                        properties: {
                            page: {
                                margin: {
                                    top: 1440,
                                    bottom: 1440,
                                    left: 1440,
                                    right: 1440,
                                },
                            },
                        },
                        children: paragraphs,
                    },
                ],
            });

            const blob = await Packer.toBlob(doc);

            const fallbackName = ensureDocxExtension(
                sanitizeFileName(buildFallbackFileName(trimmedCompanyName, trimmedAir))
            );

            const url = window.URL.createObjectURL(blob);
            const anchor = document.createElement('a');
            anchor.href = url;
            anchor.download = fallbackName;
            document.body.appendChild(anchor);
            anchor.click();
            document.body.removeChild(anchor);
            window.URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Failed to generate summary Word document:', err);
            setError('Unable to generate the summary right now. Please try again later.');
        } finally {
            setIsGenerating(false);
        }
    };



    return (
        <div className="focus-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="focus-mode-title">
            <div className="focus-modal">
                <button
                    type="button"
                    className="focus-modal__close"
                    onClick={handleDisableClick}
                    aria-label="Close focus mode modal"
                >
                    <IoClose size={20} />
                </button>

                <div className="focus-modal__content">
                    <h2 id="focus-mode-title">Generate Summary</h2>
                </div>

                <form className="focus-modal__form" onSubmit={handleSubmit}>
                    <label className="focus-modal__field" htmlFor="focus-company-name">
                        <span>Company name</span>
                        <input
                            id="focus-company-name"
                            name="companyName"
                            type="text"
                            value={companyName}
                            onChange={(event) => {
                                setCompanyName(event.target.value);
                                if (error) {
                                    setError(null);
                                }
                            }}
                            placeholder="Enter company name"
                            disabled={isGenerating}
                        />
                    </label>

                    <label className="focus-modal__field" htmlFor="focus-air">
                        <span>Year</span>
                        <input
                            id="focus-air"
                            name="air"
                            type="text"
                            value={air}
                            onChange={(event) => {
                                setAir(event.target.value);
                                if (error) {
                                    setError(null);
                                }
                            }}
                            placeholder="Enter Year"
                            disabled={isGenerating}
                        />
                    </label>

                    <div className="focus-modal__actions">

                        <button
                            type="button"
                            className="btn-outline"
                            onClick={handleGenerateSummary}
                            disabled={isGenerating}
                            aria-busy={isGenerating}
                        >
                            {isGenerating ? 'Generating...' : 'Generate Summary'}
                        </button>
                        <button type="button" className="btn-primary" onClick={handleDisableClick} disabled={isGenerating}>
                            Go Back
                        </button>
                    </div>

                    {error && (
                        <div className="focus-modal__error" role="alert">
                            {error}
                        </div>
                    )}
                </form>
            </div>
        </div>
    );
};

export default FocusModeModal;
