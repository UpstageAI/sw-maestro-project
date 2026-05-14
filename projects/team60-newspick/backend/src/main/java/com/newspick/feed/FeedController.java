package com.newspick.feed;

import com.newspick.category.CategoryCatalog;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class FeedController {

    private final FeedService feedService;

    public FeedController(FeedService feedService) {
        this.feedService = feedService;
    }

    @GetMapping("/feed")
    public FeedResponse getFeed(
            @RequestParam(name = "categories", required = false) String categories
    ) {
        return new FeedResponse(feedService.listFeed(CategoryCatalog.parseIds(categories)));
    }
}
