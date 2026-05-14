import type { Agent, AgentOpinion } from '@/types';
import { SectionTitle } from '@/components/common';
import { UserInputBanner } from './UserInputBanner';
import { OpinionGrid } from './OpinionGrid';
import { Button } from '@/components/ui/button';
import { Info } from 'lucide-react';
import { consultationContent } from '@/content';

interface OpinionPhaseProps {
  userInput: string;
  agents: Agent[];
  opinions: AgentOpinion[];
  onEditInput?: () => void;
}

export function OpinionPhase({ userInput, agents, opinions, onEditInput }: OpinionPhaseProps) {
  return (
    <div className="flex flex-col gap-6">
      <UserInputBanner userInput={userInput} onEdit={onEditInput} />
      <SectionTitle
        title={consultationContent.round1.title}
        subtitle={consultationContent.round1.description}
        action={
          <Button variant="outline" size="sm" className="gap-1.5 text-xs">
            라운드 안내
            <Info className="size-3.5" />
          </Button>
        }
      />
      <OpinionGrid agents={agents} opinions={opinions} />
    </div>
  );
}
