//
// Copyright 2025 Element Creations Ltd.
// Copyright 2022-2025 New Vector Ltd.
//
// SPDX-License-Identifier: AGPL-3.0-only.
// Please see LICENSE files in the repository root for full details.
//

import Algorithms
import UIKit

nonisolated struct TextRoomTimelineItem: TextBasedRoomTimelineItem, Equatable {
    let id: TimelineItemIdentifier
    let timestamp: Date
    let isOutgoing: Bool
    let isEditable: Bool
    let canBeRepliedTo: Bool
    var shouldBoost = false
    
    let sender: TimelineItemSender
    
    let content: TextRoomTimelineItemContent
    
    var properties = RoomTimelineItemProperties()
    
    var body: String {
        content.body
    }
    
    var contentType: EventBasedMessageTimelineItemContentType {
        .text(content)
    }
    
    var links: [URL] {
        guard let attributedString = content.formattedBody else {
            return []
        }
        
        let links = attributedString.runs.compactMap { (run: AttributedString.Runs.Run) -> URL? in
            if run.link == nil {
                return nil
            }
            
            guard run.seventwos.eventOnRoomAlias == nil,
                  run.seventwos.eventOnRoomID == nil,
                  run.seventwos.roomAlias == nil,
                  run.seventwos.roomID == nil,
                  run.seventwos.userID == nil else {
                return nil
            }
            
            return run.link
        }
        
        return Array(links.uniqued())
    }
}
